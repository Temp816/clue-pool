<template>
  <div class="app">
    <router-view />
    <van-tabbar v-if="showTabbar" route fixed placeholder safe-area-inset-bottom>
      <van-tabbar-item to="/" icon="orders-o">线索池</van-tabbar-item>
      <van-tabbar-item v-if="canSubmit" to="/submit" icon="add-o">提线索</van-tabbar-item>
      <van-tabbar-item v-if="isAdmin" to="/admin" icon="setting-o">管理</van-tabbar-item>
      <van-tabbar-item to="/mine" icon="user-o">我的</van-tabbar-item>
    </van-tabbar>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const user = ref(JSON.parse(localStorage.getItem('user') || 'null'))
watch(() => route.path, () => {
  user.value = JSON.parse(localStorage.getItem('user') || 'null')
})
const showTabbar = computed(() => !['/login', '/welcome'].includes(route.path))
const canSubmit = computed(() => user.value?.roles?.includes('submitter'))
const isAdmin = computed(() => user.value?.roles?.includes('admin'))
</script>

<style>
:root {
  --brand: #1989fa;
  --van-primary-color: #2b6cff;
  --van-border-radius-lg: 12px;
}
body { background: #f4f6fa; margin: 0; font-family: -apple-system, 'PingFang SC', 'Microsoft YaHei', sans-serif; }
.app { max-width: 640px; margin: 0 auto; min-height: 100vh; background: #f4f6fa; box-shadow: 0 0 24px rgba(0,0,0,.04); }
.page { padding-bottom: 60px; }
/* 统一卡片质感 */
.clue-card, .user-card, .van-cell-group--inset { box-shadow: 0 2px 12px rgba(25, 137, 250, .06); }
.van-button--primary:not(.van-button--plain) { background: linear-gradient(135deg, #2b6cff, #4d8dff); border: none; }
.van-tabbar { box-shadow: 0 -2px 12px rgba(0,0,0,.05); }
</style>
