// https://nuxt.com/docs/api/configuration/nuxt-config
// @ts-ignore - defineNuxtConfig is auto-imported by Nuxt
export default defineNuxtConfig({
  modules: ["@nuxt/image"],
  routeRules: {
    '/': { redirect: { to: '/getting-started/introduction', statusCode: 301 } },
    // Pre-render all routes for static generation on Vercel
    '/**': { prerender: true }
  },
  nitro: {
    prerender: {
      crawlLinks: true,
      routes: ['/']
    }
  }
})