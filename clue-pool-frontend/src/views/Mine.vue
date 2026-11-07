<template>
  <div class="page">
    <div class="profile">
      <div class="avatar-wrap" @click="avatarInput?.click()">
        <van-image v-if="user?.avatar" round width="64" height="64" :src="user.avatar" />
        <div v-else class="avatar-ph">{{ user?.name?.slice(0, 1) }}</div>
        <div class="avatar-edit"><van-icon name="photograph" size="12" /></div>
      </div>
      <input ref="avatarInput" type="file" accept="image/*" hidden @change="uploadAvatar" />
      <div class="info">
        <h3>{{ user?.name }}</h3>
        <div class="roles">
          <van-tag v-for="r in user?.role_names" :key="r" type="primary" plain>{{ r }}</van-tag>
        </div>
        <div class="perms" v-if="user?.perms !== undefined">
          <span class="perms-label">可查看：</span>
          <van-tag v-for="p in (user?.perms || '').split(',').filter(Boolean)" :key="p" type="warning" plain size="mini">{{ p }}</van-tag>
        </div>
      </div>
      <van-button size="small" plain @click="logout">退出</van-button>
    </div>

    <van-tabs v-model:active="tab" sticky>
      <van-tab title="我的提交">
        <ClueList :params="{ mine: 1 }" ref="listMine" />
      </van-tab>
      <van-tab title="我的收藏">
        <ClueList :params="{ fav: 1 }" ref="listFav" />
      </van-tab>
      <van-tab title="我的关注">
        <div class="follow-list">
          <van-empty v-if="!follows.length" description="还没有关注，去线索详情页关注提交人或主题吧" />
          <van-cell v-for="f in follows" :key="f.id" :title="f.target_name"
            :label="f.target_type === 'submitter' ? '提交人' : '信息主题'">
            <template #value>
              <van-tag :type="f.is_public ? 'primary' : 'default'">{{ f.is_public ? '公开' : '隐藏' }}</van-tag>
            </template>
          </van-cell>
        </div>
      </van-tab>
      <van-tab title="私人标签">
        <div class="follow-list">
          <van-empty v-if="!myTags.length" description="还没有私人标签，在线索详情页添加" />
          <van-cell v-for="t in myTags" :key="t.tag" :title="t.tag" :value="`${t.c} 条线索`" is-link
            @click="viewTag(t.tag)" />
        </div>
      </van-tab>
    </van-tabs>

    <van-cell-group inset style="margin-top: 16px" title="我的常用标签组合">
      <template v-if="presets.length">
        <van-cell v-for="p in presets" :key="p.id" :title="p.name"
          :label="[...p.depts, p.material, p.category, p.channel].filter(Boolean).join(' → ')">
          <template #value>
            <van-button size="mini" type="danger" plain @click="delPreset(p)">删除</van-button>
          </template>
        </van-cell>
      </template>
      <van-cell v-else title="暂无" label="在完整录入页可将当前分类组合存为常用组合" />
    </van-cell-group>

    <van-cell-group inset style="margin-top: 16px">
      <van-cell title="邀请同事 / 安装到桌面" is-link @click="$router.push('/welcome')" icon="share-o" />
      <van-cell title="修改密码" is-link @click="showPw = true" icon="lock" />
    </van-cell-group>

    <van-dialog v-model:show="showPw" title="修改密码" show-cancel-button @confirm="changePw">
      <van-field v-model="oldPw" type="password" label="原密码" placeholder="请输入原密码" />
      <van-field v-model="newPw" type="password" label="新密码" placeholder="请输入新密码" />
    </van-dialog>
  </div>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { showToast } from 'vant'
import api from '../api'
import ClueList from '../components/ClueList.vue'

const router = useRouter()
const user = ref(JSON.parse(localStorage.getItem('user') || 'null'))
const avatarInput = ref(null)
async function uploadAvatar(e) {
  const f = e.target.files[0]
  e.target.value = ''
  if (!f) return
  const fd = new FormData()
  fd.append('file', f)
  const res = await api.post('/me/avatar', fd, { headers: { 'Content-Type': 'multipart/form-data' } })
  user.value = { ...user.value, avatar: res.avatar }
  localStorage.setItem('user', JSON.stringify(user.value))
  showToast({ type: 'success', message: '头像已更新' })
}
const tab = ref(0)
const follows = ref([])
const myTags = ref([])
const showPw = ref(false)
const oldPw = ref('')
const newPw = ref('')
const listMine = ref(null)
const listFav = ref(null)
const presets = ref([])

async function loadPresets() { presets.value = await api.get('/presets') }
async function delPreset(p) {
  await api.delete(`/presets/${p.id}`)
  showToast('已删除')
  loadPresets()
}

async function loadFollows() {
  const res = await api.get('/follows')
  follows.value = res.follows
}
async function loadTags() {
  myTags.value = await api.get('/my-tags')
}
watch(tab, v => {
  if (v === 2) loadFollows()
  if (v === 3) loadTags()
  if (v === 0) listMine.value?.reload()
  if (v === 1) listFav.value?.reload()
})

function viewTag(tag) {
  router.push({ path: '/', query: { my_tags: tag } })
}

async function changePw() {
  if (!newPw.value) return
  await api.post('/change-password', { old: oldPw.value, new: newPw.value })
  showToast({ type: 'success', message: '密码已修改' })
  oldPw.value = newPw.value = ''
}
function logout() {
  localStorage.removeItem('token')
  localStorage.removeItem('user')
  router.replace('/login')
}

onMounted(() => { loadFollows(); loadTags(); loadPresets() })
</script>

<style scoped>
.profile { display: flex; align-items: center; gap: 14px; background: linear-gradient(135deg, #1989fa, #39b9fa); padding: 24px 20px; color: #fff; }
.profile h3 { margin: 0 0 6px; }
.info { flex: 1; }
.avatar-wrap { position: relative; cursor: pointer; }
.avatar-ph { width: 64px; height: 64px; border-radius: 50%; background: rgba(255,255,255,.25); border: 2px solid rgba(255,255,255,.6); display: flex; align-items: center; justify-content: center; font-size: 26px; font-weight: 600; }
.avatar-edit { position: absolute; right: -2px; bottom: -2px; width: 20px; height: 20px; border-radius: 50%; background: #fff; color: #1989fa; display: flex; align-items: center; justify-content: center; box-shadow: 0 1px 4px rgba(0,0,0,.2); }
.roles { display: flex; gap: 6px; }
.perms { margin-top: 6px; display: flex; align-items: center; gap: 4px; }
.perms-label { font-size: 11px; opacity: .85; }
.follow-list { background: #fff; min-height: 200px; }
.tip { color: #969799; font-size: 12px; text-align: center; padding: 10px; }
</style>
