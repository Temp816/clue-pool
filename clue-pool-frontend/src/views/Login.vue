<template>
  <div class="login-page">
    <div class="brand">
      <div class="logo">🔍</div>
      <h1>线索池</h1>
      <p class="dept">原价中心 · SCC</p>
      <p>广泛收集 · 按需取用 · 持续深挖</p>
    </div>
    <van-form @submit="onSubmit" class="form">
      <van-field v-model="username" name="username" label="用户名" placeholder="请输入用户名"
        :rules="[{ required: true, message: '请输入用户名' }]" />
      <van-field v-model="password" type="password" name="password" label="密码" placeholder="请输入密码"
        :rules="[{ required: true, message: '请输入密码' }]" />
      <div class="btn">
        <van-button round block type="primary" native-type="submit" :loading="loading">登 录</van-button>
      </div>
      <p class="tip">账号由管理员统一分配，如需开通请联系管理员</p>
    </van-form>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { showToast } from 'vant'
import api from '../api'

const router = useRouter()
const username = ref('')
const password = ref('')
const loading = ref(false)

async function onSubmit() {
  loading.value = true
  try {
    const res = await api.post('/login', { username: username.value, password: password.value })
    localStorage.setItem('token', res.token)
    localStorage.setItem('user', JSON.stringify(res.user))
    showToast({ type: 'success', message: `欢迎，${res.user.name}` })
    router.replace('/')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page { min-height: 100vh; background: linear-gradient(180deg, #1989fa 0%, #f7f8fa 45%); padding-top: 80px; }
.brand { text-align: center; color: #fff; margin-bottom: 36px; }
.logo { font-size: 56px; }
.brand h1 { margin: 8px 0 4px; font-size: 28px; letter-spacing: 4px; }
.brand .dept { font-size: 15px; font-weight: 600; letter-spacing: 2px; opacity: .95; margin: 0 0 4px; }
.brand p { margin: 0; opacity: .85; font-size: 13px; }
.form { margin: 0 24px; background: #fff; border-radius: 16px; overflow: hidden; box-shadow: 0 6px 24px rgba(0,0,0,.08); }
.btn { padding: 16px; }
.tip { text-align: center; color: #999; font-size: 12px; padding-bottom: 16px; margin: 0; }
</style>
