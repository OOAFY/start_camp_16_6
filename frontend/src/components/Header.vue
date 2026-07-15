<template>
  <header class="site-header">
    <div class="container header-inner">
      <router-link class="brand" to="/" aria-label="LocalHub 홈">
        <img :src="logo" alt="LocalHub 로고" class="brand-logo" />
        <span class="brand-name">LocalHub</span>
      </router-link>

      <nav class="main-nav" aria-label="주요 메뉴">
        <router-link
          v-for="link in links"
          :key="link.to"
          :to="link.to"
        >
          {{ link.label }}
        </router-link>
      </nav>

      <div class="header-spacer" aria-hidden="true"></div>
    </div>
  </header>
</template>

<script setup>
import logo from '../assets/logo.png'

const links = [
  { label: '홈', to: '/' },
  { label: '지역 둘러보기', to: '/places' },
  { label: '축제 캘린더', to: '/festivals' },
  { label: '커뮤니티', to: '/community' }
]
</script>

<style scoped>
.site-header {
  height: 82px;
  background: rgba(251, 250, 246, 0.92);
  border-bottom: 1px solid rgba(230, 227, 218, 0.55);
  backdrop-filter: blur(12px);
}
.header-inner {
  height: 100%;
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  align-items: center;
}
.brand {
  width: max-content;
  display: inline-flex;
  align-items: center;
  gap: 10px;
  color: var(--green-900);
  font-size: 28px;
  font-weight: 900;
  letter-spacing: -1.1px;
}
.brand-logo {
  display: block;
  width: 42px !important;
  min-width: 42px;
  max-width: 42px;
  height: 42px !important;
  min-height: 42px;
  max-height: 42px;
  flex-shrink: 0;
  object-fit: contain;
}
.brand-name { line-height: 1; }
.main-nav {
  height: 100%;
  display: flex;
  align-items: stretch;
  gap: 50px;
}
.main-nav a {
  position: relative;
  display: flex;
  align-items: center;
  color: var(--navy);
  font-size: 16px;
  font-weight: 750;
}
.main-nav a::after {
  content: '';
  position: absolute;
  left: 50%;
  right: 50%;
  bottom: 17px;
  height: 2px;
  background: var(--green-900);
  transition: left 160ms ease, right 160ms ease;
}
.main-nav a:hover::after,
.main-nav a.router-link-exact-active::after {
  left: 0;
  right: 0;
}
.main-nav a.router-link-exact-active {
  color: var(--green-900);
}
.header-spacer {
  min-width: 1px;
}

@media (max-width: 900px) {
  .site-header { height: auto; padding: 14px 0 10px; }
  .header-inner { grid-template-columns: 1fr; gap: 8px; }
  .brand { justify-self: center; }
  .main-nav {
    width: 100%;
    height: auto;
    justify-content: space-between;
    gap: 16px;
    overflow-x: auto;
  }
  .main-nav a { min-height: 38px; font-size: 14px; white-space: nowrap; }
  .main-nav a::after { bottom: 0; }
  .header-spacer { display: none; }
}

@media (max-width: 560px) {
  .brand { font-size: 23px; }
  .main-nav { gap: 18px; justify-content: flex-start; }
}
</style>
