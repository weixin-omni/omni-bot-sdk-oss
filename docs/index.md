---
layout: home

hero:
   name: RPA + VISION
   text: 一个基于视觉识别的微信 4.0 RPA框架
   actions:
      - theme: brand
        text: 快速开始
        link: /guide/quick-start.html
      - theme: alt
        text: GitHub
        link: https://github.com/weixin-omni/omni-bot-sdk-oss
   image:
      src: /logo.png
      alt: omni-logo
features:
   - icon: ⚡️
     title: 无延迟读取
     details: 消息获取平均延迟 0.5s
   - icon: 🛡️
     title: 运行时零侵入
     details: 不注入，不Hook
   - icon: 🧩
     title: 高效插件扩展
     details: 使用插件模式，对接Dify，OpenAI
   - icon: 🚀
     title: 支持大部分消息类型
     details: 已经解析几乎所有消息类型
---

<style>
:root {
  --vp-home-hero-name-color: transparent;
  --vp-home-hero-name-background: -webkit-linear-gradient(20deg, #34fefe 30%,#47caff 80%);

  --vp-home-hero-image-background-image: linear-gradient(-20deg, #23f0e2 50%, #47caff 30%);
  --vp-home-hero-image-filter: blur(44px);
}

@media (min-width: 640px) {
  :root {
    --vp-home-hero-image-filter: blur(56px);
  }
}

@media (min-width: 960px) {
  :root {
    --vp-home-hero-image-filter: blur(68px);
  }
}
</style>
