<template>
  <div id="app">
    <Header />
    <main :class="{ 'app-main': route.path !== '/' }">
      <router-view />
    </main>
    <ChatButton />
  </div>
</template>

<script setup>
import { useRoute } from 'vue-router'
import ChatButton from './components/ChatButton.vue'
import Header from './components/Header.vue'

const route = useRoute()
</script>

<style>
#app {
  min-height: 100vh;
}
.app-main {
  width: min(1180px, calc(100% - 48px));
  margin: 0 auto;
  padding: 40px 0 64px;
}

@media (max-width: 560px) {
  .app-main {
    width: min(100% - 24px, 520px);
    padding-top: 28px;
  }
}
</style>
