---
name: gpt-image-2-full-style-library
version: "1.0.3"
display_name: "GPT-Image2中文风格库"
display_name_en: "GPT-Image2 Style Library"
description: "Search and apply the complete awesome-gpt-image-2 prompt library, including industrial templates and hundreds of repository cases. Use for image prompt creation, style selection, product KV, posters, photography, UI, infographics, illustration, characters, scenes, brand visuals, and multi-style image concepts."
description_zh: "检索并应用完整的 GPT-Image2 风格模板与案例库，用于作图提示词生成、风格匹配、产品KV、电商主图、海报、摄影、UI、信息图、插画、人物及多风格视觉创作。"
description_en: "Search and apply the complete GPT-Image2 style template and case library for image prompt creation, style matching, product KV, e-commerce visuals, posters, photography, UI, infographics, illustration, characters, and multi-style concepts."
---

# GPT-Image2 风格模板库｜WorkBuddy 中文适配版

本 Skill 为基于开源项目 `awesome-gpt-image-2` 制作的非官方 WorkBuddy 中文适配版本，主要进行格式兼容、中文检索与使用场景适配，不代表与原作者存在合作、代理或官方关联。

Use the repository templates and cases to turn an image request into a production-ready prompt or, when image generation is available and requested, generate the image.

This is the repository-based full library. It contains no personal user preferences or private house style.

## Required routing

1. Read `references/style-library.md` to identify the closest template, style tags, and scene tags.
   For exact library coverage and per-category counts, read `references/full-library-index.md`.
2. Read `references/industrial-templates.md` when a reusable production template is needed.
3. Read only the relevant category case file from the list below. Search its headings, titles, styles, scenes, and prompt text for the nearest examples.
4. Select 1-3 useful cases. Borrow their visual mechanism, composition, lighting, materials, palette, and prompt structure; do not blindly copy an unrelated brand, product, person, title, or slogan.
5. Build the final prompt with: subject, composition, environment, lighting, material, palette, text rules, aspect ratio, fidelity constraints, and negative constraints.

## Case routing

- UI and interfaces: `references/cases-01-ui-interfaces.md`
- Charts and infographics: `references/cases-02-charts-infographics.md`
- Posters and typography: `references/cases-03-posters-typography.md`
- Products and e-commerce: `references/cases-04-products-ecommerce.md`
- Brand and logos: `references/cases-05-brand-logos.md`
- Architecture and spaces: `references/cases-06-architecture-spaces.md`
- Photography and realism: `references/cases-07-photography-realism.md`
- Illustration and art: `references/cases-08-illustration-art.md`
- Characters and people: `references/cases-09-characters-people.md`
- Scenes and storytelling: `references/cases-10-scenes-storytelling.md`
- History and classical themes: `references/cases-11-history-classical.md`
- Documents and publishing: `references/cases-12-documents-publishing.md`
- Other use cases: `references/cases-13-other-use-cases.md`

## Output behavior

- Detect the user's language and respond in that language.
- If the user asks to generate directly, do the routing internally and do not expose analysis unless requested.
- If the user asks only for a prompt, provide the copyable prompt first and optionally name the selected template and case IDs.
- For multiple concepts, make each concept materially different in composition, space, lighting, palette, scale, and visual idea. Do not merely change the background color.
- When multiple images are requested, each result must be a separate image unless the user explicitly requests a collage.
- Uploaded product/reference images have priority for identity, shape, structure, proportions, colors, materials, and visible details.
- Respect explicit requests about text and logos. If the user requests no external text or logo, remove all external titles, slogans, badges, prices, and marks from the final prompt.

## Fidelity and safety defaults

Avoid changing product identity, inventing features or claims, adding incorrect logos, producing gibberish text, distorting structure, duplicating subjects, using implausible floating, creating cheap template effects, or adding watermarks and QR codes.

## 来源与使用说明

本 Skill 参考并基于开源项目 [awesome-gpt-image-2](https://github.com/freestylefly/awesome-gpt-image-2) 的案例分类、提示词结构与模板思路，结合 WorkBuddy 及中文 AI 作图场景进行中文化整理与使用适配。

- 原项目作者：[freestylefly（苍何）](https://github.com/freestylefly)
- 原项目仓库：https://github.com/freestylefly/awesome-gpt-image-2
- 原案例效果图与模板参考：https://gpt-image2.canghe.ai/#templates

原项目采用 MIT License 开源协议。本 Skill 已保留原项目来源及许可证信息，仅作学习交流、提示词研究与中文作图场景适配。使用者应同时遵守原项目许可证以及所使用 AI 平台的相关规则。

本 Skill 为非官方中文适配版本，不收费、不售卖，不用于课程、会员、引流或其他直接商业用途。该说明仅用于说明本整理版本的发布与分享方式，不改变原项目 MIT License 所授予的权利，也不代表与原作者存在合作、代理或官方关联。

本 Skill 不收录或再发布原案例效果图片。涉及第三方品牌、人物、作品或其他素材时，仅可在具备相应使用权或获得授权的前提下使用；如相关权利人认为内容存在不妥，可联系发布者进行修改、删除或下架处理。
