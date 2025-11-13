// https://nuxt.com/docs/api/configuration/nuxt-config
// @ts-ignore - defineNuxtConfig is auto-imported by Nuxt
export default defineNuxtConfig({
  modules: ["@nuxt/image"],
  routeRules: {
    '/': { redirect: '/getting-started/introduction' }
  },
  ui: {
    colors: {
      primary: 'blue',
      neutral: 'zinc'
    }
  }
})