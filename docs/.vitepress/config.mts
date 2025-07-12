import { defineConfig } from 'vitepress'
import {
  groupIconMdPlugin,
  groupIconVitePlugin,
  localIconLoader,
} from 'vitepress-plugin-group-icons'
import llmstxt from 'vitepress-plugin-llms'
import { withMermaid } from "vitepress-plugin-mermaid";

export default withMermaid({
  lang: 'zh-CN',
  title: 'omni-bot',
  description: '🤖 一个基于视觉识别的微信4.0 RPA框架',
  cleanUrls: true,
  head: [
    ['link', { rel: 'icon', href: '/favicon.ico' }],
    ['meta', { name: 'theme-color', content: '#67e8e2' }],
    ['meta', { property: 'og:type', content: 'website' }],
    ['meta', { property: 'og:locale', content: 'zh-CN' }],
    ['meta', { property: 'og:title', content: '🤖 一个基于视觉识别的微信4.0 RPA框架' }],
    ['meta', { property: 'og:site_name', content: 'omni-bot' }],
/*     ['meta', { property: 'og:image', content: 'https://yutto.nyakku.moe/logo.png' }],
    ['meta', { property: 'og:url', content: 'https://yutto.nyakku.moe/' }], */
  ],
  themeConfig: {
    logo: { src: '/logo.png', width: 24, height: 24 },
    nav: [
      { text: '首页', link: '/' },
      { text: '指南', link: '/guide/quick-start' },
      {
        text: '支持我',
        items: [
          { text: '赞助', link: '/sponsor' },
          {
            text: '参与贡献',
            link: 'https://github.com/weixin-omni/omni-bot-sdk-oss/blob/master/CONTRIBUTING.md',
          },
        ],
      },
    ],

    sidebar: {
      '/guide': [
        {
          text: '快速开始',
          link: '/guide/quick-start',
        },
        {
          text: '基础概念',
          link: '/guide/concepts',
        },
        {
          text: '配置指南',
          link: '/guide/configuration',
        },
        {
          text: '消息处理',
          link: '/guide/message-handling',
        },
        {
          text: '插件开发',
          link: '/guide/plugins',
        },
        {
          text: 'Dify 接入',
          link: '/guide/dify-integration',
        },
        {
          text: 'RPA操作',
          link: '/guide/rpa-operations',
        },
        {
          text: 'MCP集成',
          link: '/guide/mcp-integration',
        },
        {
          text: '部署指南',
          link: '/guide/deployment',
        },
        {
          text: '故障排除',
          link: '/guide/troubleshooting',
        },
        {
          text: 'FAQ',
          link: '/guide/faq',
        },
      ],
    },

    footer: {
      message: 'Released under the GPL3.0 License.',
      copyright: 'Copyright © 2025-present weixin-omni',
    },

    editLink: {
      pattern: 'https://github.com/weixin-omni/omni-bot-sdk-oss/edit/master/docs/:path',
      text: '修订此文档',
    },

    socialLinks: [
      { icon: 'github', link: 'https://github.com/weixin-omni/omni-bot-sdk-oss' },
    ],

    search: {
      provider: 'local',
    },
  },
  mermaid:{
    //mermaidConfig !theme here works for ligth mode since dark theme is forced in dark mode
  },
  markdown: {
    image: {
      lazyLoading: true,
    },
    config(md) {
      md.use(groupIconMdPlugin)
    },
  },
  vite: {
    plugins: [
      llmstxt(),
      groupIconVitePlugin({
        customIcon: {
          yutto: localIconLoader(import.meta.url, '../public/favicon.ico'),
        },
      }) as any,
    ],
  },
})
