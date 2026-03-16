#!/usr/bin/env python3
"""测试 Skill 向量检索功能."""

import os
from pathlib import Path

# 配置
MILVUS_HOST = "10.195.28.136"
MILVUS_PORT = 19530
COLLECTION_NAME = "ownbot_skills"
EMBEDDING_MODEL = "BAAI/bge-m3"
SKILLS_DIR = Path(__file__).parent / "ownbot" / "skills"


def test_milvus_connection():
    """测试 Milvus 连接."""
    print("=" * 60)
    print("测试 1: Milvus 连接")
    print("=" * 60)
    
    try:
        from pymilvus import MilvusClient
        
        client = MilvusClient(uri=f"http://{MILVUS_HOST}:{MILVUS_PORT}")
        print(f"✅ 连接到 Milvus 服务器: {MILVUS_HOST}:{MILVUS_PORT}")
        
        # 列出集合
        collections = client.list_collections()
        print(f"📁 现有集合: {collections}")
        
        # 检查 ownbot_skills 集合
        if COLLECTION_NAME in collections:
            print(f"✅ 集合 '{COLLECTION_NAME}' 存在")
            
            # 获取集合信息
            stats = client.get_collection_stats(COLLECTION_NAME)
            print(f"📊 集合统计: {stats}")
            
            # 获取实体数量
            count = client.num_entities(COLLECTION_NAME)
            print(f"📈 实体数量: {count}")
        else:
            print(f"⚠️ 集合 '{COLLECTION_NAME}' 不存在")
        
        return client
        
    except Exception as e:
        print(f"❌ 连接失败: {e}")
        return None


def test_embedding_model():
    """测试 Embedding 模型."""
    print("\n" + "=" * 60)
    print("测试 2: Embedding 模型")
    print("=" * 60)
    
    try:
        from sentence_transformers import SentenceTransformer
        
        print(f"🔄 加载模型: {EMBEDDING_MODEL}...")
        model = SentenceTransformer(EMBEDDING_MODEL)
        
        # 获取维度
        dim = model.get_sentence_embedding_dimension()
        print(f"✅ 模型加载成功")
        print(f"📐 嵌入维度: {dim}")
        
        # 测试编码
        test_texts = [
            "查询天气信息",
            "翻译文本内容",
            "搜索网络信息"
        ]
        
        print(f"🧪 测试编码 {len(test_texts)} 个文本...")
        embeddings = model.encode(test_texts)
        print(f"✅ 编码成功，形状: {embeddings.shape}")
        
        return model
        
    except Exception as e:
        print(f"❌ 模型加载失败: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_search(client, model):
    """测试向量搜索."""
    print("\n" + "=" * 60)
    print("测试 3: 向量搜索")
    print("=" * 60)
    
    if client is None or model is None:
        print("❌ 缺少 client 或 model，跳过测试")
        return
    
    try:
        # 测试查询
        queries = [
            "今天天气怎么样",
            "帮我翻译这段话",
            "搜索一下新闻"
        ]
        
        for query in queries:
            print(f"\n🔍 查询: '{query}'")
            
            # 编码查询
            query_vector = model.encode([query])[0].tolist()
            
            # 搜索
            results = client.search(
                collection_name=COLLECTION_NAME,
                data=[query_vector],
                limit=3,
                output_fields=["name", "description", "keywords"]
            )
            
            print(f"   找到 {len(results[0])} 个结果:")
            for i, result in enumerate(results[0], 1):
                entity = result["entity"]
                score = 1.0 - result["distance"]
                print(f"   {i}. {entity.get('name', 'N/A')} (相似度: {score:.3f})")
                print(f"      描述: {entity.get('description', 'N/A')[:50]}...")
                
    except Exception as e:
        print(f"❌ 搜索失败: {e}")
        import traceback
        traceback.print_exc()


def test_skill_retriever():
    """测试 SkillRetriever 类."""
    print("\n" + "=" * 60)
    print("测试 4: SkillRetriever 类")
    print("=" * 60)
    
    try:
        from ownbot.retrieval import SkillRetriever
        
        retriever = SkillRetriever(
            skills_dir=SKILLS_DIR,
            use_milvus_lite=False,
            milvus_host=MILVUS_HOST,
            milvus_port=MILVUS_PORT,
            collection_name=COLLECTION_NAME,
            embedding_model=EMBEDDING_MODEL
        )
        
        print(f"✅ SkillRetriever 初始化成功")
        
        # 测试搜索
        query = "天气怎么样"
        print(f"\n🔍 测试搜索: '{query}'")
        
        results = retriever.search(query, top_k=5)
        print(f"✅ 找到 {len(results)} 个结果:")
        
        for i, skill in enumerate(results, 1):
            print(f"   {i}. {skill.name} (得分: {skill.score:.3f})")
            print(f"      描述: {skill.description[:60]}...")
            
    except Exception as e:
        print(f"❌ SkillRetriever 测试失败: {e}")
        import traceback
        traceback.print_exc()


def main():
    """主函数."""
    print("🚀 开始测试向量检索功能\n")
    
    # 测试 1: Milvus 连接
    client = test_milvus_connection()
    
    # 测试 2: Embedding 模型
    model = test_embedding_model()
    
    # 测试 3: 向量搜索
    test_search(client, model)
    
    # 测试 4: SkillRetriever 类
    test_skill_retriever()
    
    print("\n" + "=" * 60)
    print("测试完成!")
    print("=" * 60)


if __name__ == "__main__":
    main()
