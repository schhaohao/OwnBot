---
name: translate
description: Translate text between multiple languages using Google Translate API (no API key required).
homepage: https://translate.google.com
metadata:
  ownbot:
    emoji: "🌐"
    keywords: [translate, translation, language, english, chinese, 翻译, 中文, 英文]
    use_cases:
      - "Translate 'hello' to Chinese"
      - "How do you say 'weather' in Japanese?"
      - "把'你好'翻译成英文"
      - "Translate this paragraph to Spanish"
    category: productivity
    requires:
      bins: ["curl"]
---

# Translate Skill

使用 Google Translate API 进行文本翻译，支持多种语言互译。

## 使用方法

**重要：使用 `web_request` 工具进行翻译，不要尝试使用不存在的 `translate` 工具。**

调用 `web_request` 工具，参数如下：

```json
{
  "url": "https://translate.googleapis.com/translate_a/single?client=gtx&sl={source_lang}&tl={target_lang}&dt=t&q={encoded_text}",
  "method": "GET"
}
```

## 参数说明

- `sl`: 源语言代码 (source language)
  - `auto`: 自动检测
  - `zh`: 中文
  - `en`: 英语
  - `ja`: 日语
  - `ko`: 韩语
  - `fr`: 法语
  - `de`: 德语
  - `es`: 西班牙语
  - `ru`: 俄语
  - 更多语言代码参考 ISO 639-1 标准
- `tl`: 目标语言代码 (target language)
- `q`: 要翻译的文本（需要进行 URL 编码）
- `dt=t`: 返回翻译文本

## 完整示例

### 翻译英文到中文

用户说："把 'Hello World' 翻译成中文"

调用工具：
```json
{
  "url": "https://translate.googleapis.com/translate_a/single?client=gtx&sl=en&tl=zh&dt=t&q=Hello%20World",
  "method": "GET"
}
```

### 翻译中文到英文

用户说："翻译 '你好世界' 成英语"

调用工具：
```json
{
  "url": "https://translate.googleapis.com/translate_a/single?client=gtx&sl=zh&tl=en&dt=t&q=%E4%BD%A0%E5%A5%BD%E4%B8%96%E7%95%8C",
  "method": "GET"
}
```

### 自动检测语言

用户说："翻译 'Bonjour'"

调用工具（使用 `sl=auto` 自动检测源语言）：
```json
{
  "url": "https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl=zh&dt=t&q=Bonjour",
  "method": "GET"
}
```

## 响应格式

API 返回 JSON 数组格式：
```json
[[["你好世界", "Hello World", null, null, 1]], null, "en"]
```

- 第一个元素是翻译结果数组
- 每个翻译项格式：`[翻译文本, 原文, 其他信息...]`
- 最后一个元素是检测到的源语言代码

## 常见使用场景

用户可能会说：
- "把 {text} 翻译成 {language}"
- "翻译 '{text}' 成 {language}"
- "这句话用 {language} 怎么说：{text}"
- "{text} 的 {language} 是什么"
- "帮我翻译：{text}"

## 语言代码速查

| 语言 | 代码 | 语言 | 代码 |
|------|------|------|------|
| 中文 | zh | 英语 | en |
| 日语 | ja | 韩语 | ko |
| 法语 | fr | 德语 | de |
| 西班牙语 | es | 俄语 | ru |
| 意大利语 | it | 葡萄牙语 | pt |
| 阿拉伯语 | ar | 泰语 | th |
| 越南语 | vi | 印尼语 | id |

## 注意事项

1. **必须使用 `web_request` 工具**，不要尝试调用不存在的 `translate` 工具
2. 文本需要进行 URL 编码，特别是非 ASCII 字符（中文、日文等）
3. 如果不确定源语言，使用 `sl=auto` 让 Google 自动检测
4. 如果用户没有指定目标语言，默认翻译成中文（`tl=zh`）或英语（`tl=en`）
5. 返回的结果需要解析 JSON 数组，提取第一个翻译项的第一个元素
