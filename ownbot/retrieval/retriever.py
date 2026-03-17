"""Skill retriever using Milvus for vector search."""

from __future__ import annotations

import math
import os
import re
import socket
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from loguru import logger


@dataclass
class SkillSearchResult:
    """Result of a skill search."""
    
    name: str
    description: str
    path: str
    score: float
    metadata: dict[str, Any]
    
    def to_summary(self) -> str:
        """Generate a brief summary for system prompt."""
        return f"- {self.name}: {self.description}"


class SkillRetriever:
    """
    Retriever for skills using vector search.
    
    This class handles:
    1. Building vector index from skill metadata
    2. Searching relevant skills by query
    3. Returning skill summaries (not full content)
    
    The full skill content is loaded on-demand by the agent.
    
    Embedding model is configurable, and dimension is automatically detected.
    """
    
    # Common embedding models and their dimensions
    # Used as fallback if auto-detection fails
    MODEL_DIMENSIONS = {
        # sentence-transformers models
        "all-MiniLM-L6-v2": 384,
        "all-MiniLM-L12-v2": 384,
        "all-distilroberta-v1": 768,
        "all-mpnet-base-v2": 768,
        "paraphrase-MiniLM-L6-v2": 384,
        "paraphrase-multilingual-MiniLM-L12-v2": 384,
        "distiluse-base-multilingual-cased-v1": 512,
        "distiluse-base-multilingual-cased-v2": 512,
        # BAAI models (FlagEmbedding)
        "BAAI/bge-m3": 1024,
        "BAAI/bge-large-zh": 1024,
        "BAAI/bge-base-zh": 768,
        "BAAI/bge-small-zh": 512,
        "BAAI/bge-large-en": 1024,
        "BAAI/bge-base-en": 768,
    }
    
    def __init__(
        self,
        skills_dir: Path,
        use_milvus_lite: bool = True,
        milvus_host: str = "localhost",
        milvus_port: int = 19530,
        milvus_db_path: str = "./milvus_data/ownbot.db",
        collection_name: str = "ownbot_skills",
        embedding_model: str = "BAAI/bge-m3",
    ):
        """
        Initialize the skill retriever.
        
        Args:
            skills_dir: Directory containing skill subdirectories
            use_milvus_lite: Use Milvus Lite (embedded) instead of Milvus server
            milvus_host: Milvus server host (only used if use_milvus_lite=false)
            milvus_port: Milvus server port (only used if use_milvus_lite=false)
            milvus_db_path: Path to Milvus Lite database file
            collection_name: Name of the Milvus collection
            embedding_model: Embedding model name (e.g., "BAAI/bge-m3", "all-MiniLM-L6-v2")
        """
        self.skills_dir = skills_dir
        self.use_milvus_lite = use_milvus_lite
        self.milvus_host = milvus_host
        self.milvus_port = milvus_port
        self.milvus_db_path = milvus_db_path
        self.collection_name = collection_name
        self.embedding_model = embedding_model
        
        self._client = None
        self._embedding_fn = None
        self._embedding_dim: int | None = None
        self._initialized = False
        self._use_fallback = False
        self._fallback_ready = False
        self._fallback_use_embeddings = False
        self._fallback_index: list[dict[str, Any]] = []
    
    def _get_client(self):
        """Lazy initialization of Milvus client."""
        if self._client is None and not self._use_fallback:
            try:
                from pymilvus import MilvusClient
                
                if self.use_milvus_lite:
                    # Use Milvus Lite (embedded)
                    if not self._can_use_milvus_lite():
                        self._use_fallback = True
                        return None
                    raw_path = os.path.expanduser(self.milvus_db_path)
                    db_path = os.path.abspath(raw_path)
                    if not db_path.endswith(".db"):
                        db_path = os.path.join(db_path, "ownbot.db")

                    os.makedirs(os.path.dirname(db_path), exist_ok=True)
                    logger.info("Connecting to Milvus Lite at {}", db_path)
                    self._client = MilvusClient(uri=db_path)
                    
                else:
                    # Use Milvus server
                    host = self.milvus_host or "127.0.0.1"
                    uri_str = f"http://{host}:{self.milvus_port}"

                    logger.info("Connecting to Milvus server at {}", uri_str)
                    self._client = MilvusClient(uri=uri_str)
                    logger.info("Connected to Milvus server at {}:{}", host, self.milvus_port)
                    
            except ImportError as e:
                logger.warning("pymilvus not installed, falling back to in-memory index: {}", e)
                self._use_fallback = True
                self._client = None
            except Exception as e:
                logger.warning("Failed to connect to Milvus, falling back to in-memory index: {}", e)
                self._use_fallback = True
                self._client = None
        return self._client

    def _can_use_milvus_lite(self) -> bool:
        """Check whether Unix domain sockets are permitted for Milvus Lite."""
        if os.environ.get("CODEX_SANDBOX"):
            logger.warning("Codex sandbox detected; using in-memory index instead of Milvus Lite.")
            return False
        if os.environ.get("OWNBOT_DISABLE_MILVUS_LITE", "").lower() in {"1", "true", "yes"}:
            logger.warning("OWNBOT_DISABLE_MILVUS_LITE is set; using in-memory index.")
            return False

        sock_dir = Path(tempfile.gettempdir())
        sock_path = sock_dir / f"ownbot_{os.getpid()}.sock"
        sock = None
        try:
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.bind(str(sock_path))
            return True
        except OSError as e:
            logger.warning(
                "Milvus Lite UDS bind not permitted in {} ({}). Falling back to in-memory index.",
                sock_dir,
                e,
            )
            return False
        finally:
            if sock is not None:
                try:
                    sock.close()
                except OSError:
                    pass
            try:
                sock_path.unlink(missing_ok=True)
            except OSError:
                pass
    
    def _get_embedding_fn(self):
        """Lazy initialization of embedding function."""
        if self._embedding_fn is None:
            try:
                from sentence_transformers import SentenceTransformer
                logger.info("Loading embedding model: {}...", self.embedding_model)
                self._embedding_fn = SentenceTransformer(self.embedding_model)
                logger.info("Loaded embedding model: {}", self.embedding_model)
            except ImportError:
                logger.error("sentence-transformers not installed. Run: pip install sentence-transformers")
                raise
            except Exception as e:
                logger.error("Failed to load embedding model '{}': {}", self.embedding_model, e)
                raise
        return self._embedding_fn

    def _tokenize(self, text: str) -> set[str]:
        return set(re.findall(r"[a-z0-9_]+", text.lower()))

    def _cosine_sim(self, vec_a, vec_b) -> float:
        dot = 0.0
        norm_a = 0.0
        norm_b = 0.0
        for a, b in zip(vec_a, vec_b):
            dot += a * b
            norm_a += a * a
            norm_b += b * b
        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0
        return dot / math.sqrt(norm_a * norm_b)

    def _iter_skill_dirs(self) -> list[Path]:
        """Return valid skill directories under the configured skills root."""
        if not self.skills_dir.exists():
            return []
        return [
            item for item in self.skills_dir.iterdir()
            if item.is_dir() and not item.name.startswith("_") and (item / "SKILL.md").exists()
        ]

    def _collect_skill_metadata(self) -> list[dict[str, Any]]:
        """Read metadata for all workspace skills."""
        skills = []
        for item in self._iter_skill_dirs():
            metadata = self._extract_skill_metadata(item)
            if metadata:
                skills.append(metadata)
        return skills

    def _count_skill_dirs(self) -> int:
        """Count workspace skills currently on disk."""
        return len(self._iter_skill_dirs())

    def _build_fallback_index(self, force_rebuild: bool = False) -> int:
        if self._fallback_ready and not force_rebuild:
            return 0

        skills = self._collect_skill_metadata()

        if not skills:
            self._fallback_index = []
            self._fallback_ready = True
            self._fallback_use_embeddings = False
            logger.info("No workspace skills found in {}", self.skills_dir)
            return 0

        search_texts = [s["search_text"] for s in skills]
        vectors = None
        use_embeddings = os.environ.get("OWNBOT_FALLBACK_USE_EMBEDDINGS", "").lower() in {
            "1",
            "true",
            "yes",
        }

        if use_embeddings:
            try:
                embedding_fn = self._get_embedding_fn()
                vectors = embedding_fn.encode(search_texts, show_progress_bar=False)
            except Exception as e:
                logger.warning("Embedding model unavailable, using lexical fallback: {}", e)
                use_embeddings = False

        self._fallback_index = []
        if use_embeddings and vectors is not None:
            for skill, vec in zip(skills, vectors):
                vector = vec.tolist() if hasattr(vec, "tolist") else list(vec)
                self._fallback_index.append({**skill, "vector": vector})
        else:
            for skill in skills:
                tokens = self._tokenize(skill["search_text"])
                self._fallback_index.append({**skill, "tokens": tokens})

        self._fallback_use_embeddings = use_embeddings
        self._fallback_ready = True
        logger.info("Built fallback index with {} skills", len(self._fallback_index))
        return len(self._fallback_index)

    def _search_fallback(self, query: str, top_k: int) -> list[SkillSearchResult]:
        if not self._fallback_ready:
            self._build_fallback_index()

        if not self._fallback_index:
            return []

        results: list[SkillSearchResult] = []
        if self._fallback_use_embeddings:
            try:
                embedding_fn = self._get_embedding_fn()
                query_vec = embedding_fn.encode([query])[0].tolist()
                scored = []
                for item in self._fallback_index:
                    score = self._cosine_sim(query_vec, item["vector"])
                    scored.append((score, item))
            except Exception as e:
                logger.warning("Embedding query failed, switching to lexical fallback: {}", e)
                self._fallback_use_embeddings = False
                self._build_fallback_index(force_rebuild=True)
                return self._search_fallback(query, top_k)
        else:
            query_tokens = self._tokenize(query)
            scored = []
            for item in self._fallback_index:
                tokens = item.get("tokens", set())
                if not tokens and not query_tokens:
                    score = 0.0
                else:
                    union = tokens | query_tokens
                    score = len(tokens & query_tokens) / max(len(union), 1)
                scored.append((score, item))

        scored.sort(key=lambda x: x[0], reverse=True)
        for score, item in scored[:top_k]:
            results.append(
                SkillSearchResult(
                    name=item["name"],
                    description=item["description"],
                    path=item["path"],
                    score=score,
                    metadata={
                        "keywords": item.get("keywords", []),
                        "use_cases": item.get("use_cases", []),
                        "category": item.get("category", "general"),
                        "emoji": item.get("emoji", "🔧"),
                    },
                )
            )
        return results
    
    def get_embedding_dimension(self) -> int:
        """
        Get the embedding dimension from the model.
        
        Automatically detects dimension from the loaded model.
        Falls back to known dimensions lookup if needed.
        
        Returns:
            Embedding dimension (e.g., 384, 768)
        """
        if self._embedding_dim is None:
            embedding_fn = self._get_embedding_fn()
            
            # Try to get dimension from model
            try:
                # sentence-transformers models have get_sentence_embedding_dimension()
                dim = embedding_fn.get_sentence_embedding_dimension()
                if dim:
                    self._embedding_dim = dim
                    logger.info("Auto-detected embedding dimension: {}", dim)
                    return dim
            except Exception:
                pass
            
            # Fallback: lookup known dimensions
            if self.embedding_model in self.MODEL_DIMENSIONS:
                self._embedding_dim = self.MODEL_DIMENSIONS[self.embedding_model]
                logger.info("Using known embedding dimension for {}: {}", 
                          self.embedding_model, self._embedding_dim)
                return self._embedding_dim
            
            # Last resort: encode a test sentence and measure
            try:
                test_embedding = embedding_fn.encode(["test"])
                self._embedding_dim = len(test_embedding[0])
                logger.info("Measured embedding dimension: {}", self._embedding_dim)
                return self._embedding_dim
            except Exception as e:
                logger.error("Failed to determine embedding dimension: {}", e)
                raise RuntimeError(f"Cannot determine embedding dimension for {self.embedding_model}")
        
        return self._embedding_dim
    
    def _extract_skill_metadata(self, skill_path: Path) -> dict[str, Any] | None:
        """
        Extract metadata from a skill's SKILL.md file.
        
        Only reads the frontmatter, not the full content.
        
        Args:
            skill_path: Path to skill directory
            
        Returns:
            Skill metadata dict or None if invalid
        """
        skill_file = skill_path / "SKILL.md"
        if not skill_file.exists():
            return None
        
        try:
            content = skill_file.read_text(encoding="utf-8")
            
            # Extract YAML frontmatter
            match = re.match(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)
            if not match:
                logger.warning("No frontmatter found in {}", skill_file)
                return None
            
            frontmatter = yaml.safe_load(match.group(1)) or {}
            
            name = frontmatter.get("name") or skill_path.name
            description = frontmatter.get("description", "")
            
            # Extract ownbot-specific metadata
            metadata = frontmatter.get("metadata", {})
            ownbot_meta = metadata.get("ownbot", {}) if isinstance(metadata, dict) else {}
            
            # Build search text from metadata
            keywords = ownbot_meta.get("keywords", [])
            use_cases = ownbot_meta.get("use_cases", [])
            category = ownbot_meta.get("category", "general")
            
            search_text = f"{name}. {description}"
            if keywords:
                search_text += f" Keywords: {', '.join(keywords)}"
            if use_cases:
                search_text += f" Use cases: {', '.join(use_cases)}"
            if category:
                search_text += f" Category: {category}"
            
            return {
                "id": name,
                "name": name,
                "description": description,
                "path": str(skill_path),
                "search_text": search_text,
                "keywords": keywords,
                "use_cases": use_cases,
                "category": category,
                "emoji": ownbot_meta.get("emoji", "🔧"),
            }
            
        except Exception as e:
            logger.error("Failed to parse skill {}: {}", skill_path, e)
            return None
    
    def build_index(self, force_rebuild: bool = False) -> int:
        """
        Build or update the vector index for all skills.
        
        Args:
            force_rebuild: If True, delete existing collection and rebuild
            
        Returns:
            Number of skills indexed
        """
        client = self._get_client()
        if self._use_fallback or client is None:
            return self._build_fallback_index(force_rebuild=force_rebuild)

        skills = self._collect_skill_metadata()
        
        # Check if collection exists
        if client.has_collection(self.collection_name):
            if force_rebuild:
                client.drop_collection(self.collection_name)
                logger.info("Dropped existing collection: {}", self.collection_name)
            else:
                # Collection exists, return current count
                try:
                    results = client.query(
                        collection_name=self.collection_name,
                        filter="",
                        output_fields=["name"],
                        limit=10000
                    )
                    count = len(results)
                    logger.info("Collection {} already exists with {} skills, skipping build", 
                               self.collection_name, count)
                    return count
                except Exception as e:
                    logger.warning("Failed to query collection: {}", e)
                    return 0

        if not skills:
            if client.has_collection(self.collection_name):
                client.drop_collection(self.collection_name)
                logger.info(
                    "Dropped collection {} because no workspace skills were found in {}",
                    self.collection_name,
                    self.skills_dir,
                )
            logger.info("No workspace skills found in {}", self.skills_dir)
            return 0

        embedding_fn = self._get_embedding_fn()
        
        # Get embedding dimension dynamically
        dimension = self.get_embedding_dimension()
        
        # Generate embeddings
        logger.info("Generating embeddings for {} skills using {}...", 
                   len(skills), self.embedding_model)
        search_texts = [s["search_text"] for s in skills]
        embeddings = embedding_fn.encode(search_texts, show_progress_bar=True)
        
        # Create collection with dynamic dimension
        from pymilvus import DataType
        
        client.create_collection(
            collection_name=self.collection_name,
            dimension=dimension,  # Dynamic dimension from model
            auto_id=False,
            id_type=DataType.VARCHAR,
            max_length=256,
        )
        
        logger.info("Created collection '{}' with dimension {}", 
                   self.collection_name, dimension)
        
        # Prepare data for insertion
        ids = [s["id"] for s in skills]
        vectors = embeddings.tolist()
        
        # Store metadata as JSON strings
        metadatas = []
        for skill in skills:
            metadatas.append({
                "name": skill["name"],
                "description": skill["description"],
                "path": skill["path"],
                "keywords": ",".join(skill["keywords"]),
                "use_cases": ",".join(skill["use_cases"]),
                "category": skill["category"],
                "emoji": skill["emoji"],
            })
        
        client.insert(
            collection_name=self.collection_name,
            data=[
                {"id": id_, "vector": vec, **meta}
                for id_, vec, meta in zip(ids, vectors, metadatas)
            ],
        )
        
        logger.info("Successfully indexed {} skills using {}", 
                   len(skills), self.embedding_model)
        return len(skills)
    
    def search(self, query: str, top_k: int = 50) -> list[SkillSearchResult]:
        """
        Search for relevant skills by query.
        
        Args:
            query: User query text
            top_k: Number of top results to return (default 50)
            
        Returns:
            List of skill search results
        """
        logger.info(
            "Starting skill vector search: query='{}', top_k={}, backend={}",
            query,
            top_k,
            "fallback" if self._use_fallback else "milvus",
        )
        if self._use_fallback:
            results = self._search_fallback(query, top_k)
            logger.info("Skill search finished with {} result(s) via fallback backend", len(results))
            return results
        if not self._initialized:
            self._ensure_collection_exists()
        else:
            self._check_and_update_index()

        if self._count_skill_dirs() == 0:
            logger.info("Skipping workspace skill search because {} has no skills", self.skills_dir)
            return []
        
        client = self._get_client()
        embedding_fn = self._get_embedding_fn()
        
        # Generate query embedding
        query_vector = embedding_fn.encode([query])[0].tolist()
        
        # Search
        results = client.search(
            collection_name=self.collection_name,
            data=[query_vector],
            limit=top_k,
            output_fields=["name", "description", "path", "keywords", "use_cases", "category", "emoji"],
        )
        
        # Parse results
        search_results = []
        for result in results[0]:  # First (and only) query
            entity = result["entity"]
            search_results.append(SkillSearchResult(
                name=entity["name"],
                description=entity["description"],
                path=entity["path"],
                score=1.0 - result["distance"],  # Convert distance to similarity score
                metadata={
                    "keywords": entity["keywords"].split(",") if entity["keywords"] else [],
                    "use_cases": entity["use_cases"].split(",") if entity["use_cases"] else [],
                    "category": entity["category"],
                    "emoji": entity["emoji"],
                }
            ))

        logger.info("Skill search finished with {} result(s) via Milvus", len(search_results))
        return search_results
    
    def _ensure_collection_exists(self):
        """Ensure the collection exists, build if not."""
        if self._use_fallback:
            self._build_fallback_index()
            self._initialized = True
            return
        client = self._get_client()
        if self._use_fallback or client is None:
            self._build_fallback_index()
            self._initialized = True
            return
        if not client.has_collection(self.collection_name):
            logger.info("Collection not found, building index...")
            self.build_index()
        else:
            self._check_and_update_index()
        # Note: We don't check for updates here to avoid rebuilding index on every search.
        # Index updates should be done explicitly via build_index(force_rebuild=True) or index-skills command.
        self._initialized = True
    
    def _check_and_update_index(self) -> bool:
        """
        Check if the index needs to be updated and rebuild if necessary.
        
        Returns:
            True if index was rebuilt, False otherwise
        """
        if self._use_fallback:
            before = len(self._fallback_index)
            self._build_fallback_index(force_rebuild=True)
            return len(self._fallback_index) != before
        try:
            fs_skill_count = self._count_skill_dirs()
            
            # Count skills in Milvus
            client = self._get_client()
            milvus_stats = client.get_collection_stats(self.collection_name)
            milvus_count = milvus_stats.get("row_count", 0)
            
            logger.debug("Skill count - Filesystem: {}, Milvus: {}", fs_skill_count, milvus_count)
            
            # If counts differ, rebuild index
            if fs_skill_count != milvus_count:
                logger.info(
                    "Skill count mismatch detected (fs: {}, milvus: {}), rebuilding index...",
                    fs_skill_count, milvus_count
                )
                self.build_index(force_rebuild=True)
                return True
            
            return False
            
        except Exception as e:
            logger.warning("Failed to check index status: {}", e)
            return False
    
    def needs_rebuild(self) -> bool:
        """
        Check if the index needs to be rebuilt.
        
        Returns:
            True if index needs rebuild, False otherwise
        """
        try:
            client = self._get_client()
            
            # If collection doesn't exist, needs build
            if not client.has_collection(self.collection_name):
                return True
            
            fs_skill_count = self._count_skill_dirs()
            
            # Count skills in Milvus
            milvus_stats = client.get_collection_stats(self.collection_name)
            milvus_count = milvus_stats.get("row_count", 0)
            
            return fs_skill_count != milvus_count
            
        except Exception as e:
            logger.warning("Failed to check if rebuild needed: {}", e)
            return True
    
    def get_skill_summary(self, skill_name: str) -> str | None:
        """
        Get a brief summary of a skill for system prompt.
        
        Args:
            skill_name: Name of the skill
            
        Returns:
            Skill summary string or None if not found
        """
        skill_path = self.skills_dir / skill_name
        metadata = self._extract_skill_metadata(skill_path)
        
        if metadata:
            emoji = metadata.get("emoji", "🔧")
            return f"{emoji} **{metadata['name']}**: {metadata['description']}"
        
        return None
    
    def format_skills_for_prompt(self, skills: list[SkillSearchResult]) -> str:
        """
        Format a list of skills for inclusion in system prompt.
        
        Args:
            skills: List of skill search results
            
        Returns:
            Formatted string for system prompt
        """
        if not skills:
            return "No relevant skills found."
        
        lines = ["## Available Skills\n"]
        lines.append(f"You have access to the following {len(skills)} skills:\n")
        
        for skill in skills:
            emoji = skill.metadata.get("emoji", "🔧")
            lines.append(f"{emoji} **{skill.name}**: {skill.description} (doc path: {Path(skill.path) / 'SKILL.md'})")
        
        lines.append("\nTo use a skill, read the exact doc path shown above with the `read_file` tool.")
        
        return "\n".join(lines)
