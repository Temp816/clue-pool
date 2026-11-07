<template>
  <div class="page">
    <van-nav-bar title="管理后台" />

    <van-tabs v-model:active="tab" sticky>
      <!-- 数据看板 -->
      <van-tab title="数据看板">
        <div class="panel" v-if="stats">
          <div class="stat-cards">
            <div class="stat-card"><b>{{ stats.total }}</b><span>线索总数</span></div>
            <div class="stat-card"><b>{{ stats.today }}</b><span>今日新增</span></div>
            <div class="stat-card"><b>{{ stats.week }}</b><span>近7天</span></div>
            <div class="stat-card"><b>{{ stats.users }}</b><span>用户数</span></div>
          </div>

          <van-cell-group inset title="近14天提交趋势">
            <div class="trend">
              <div v-for="t in stats.trend" :key="t.d" class="trend-col">
                <div class="trend-bar" :style="{ height: barH(t.c, maxTrend) }"></div>
                <span class="trend-n">{{ t.c }}</span>
                <span class="trend-d">{{ t.d.slice(5) }}</span>
              </div>
            </div>
          </van-cell-group>

          <van-cell-group inset title="条线分布">
            <div class="dist" v-for="(n, k) in stats.by_dept" :key="k">
              <span class="dist-label">{{ k }}</span>
              <div class="dist-track"><div class="dist-fill blue" :style="{ width: pct(n, stats.total) }"></div></div>
              <span class="dist-n">{{ n }}</span>
            </div>
          </van-cell-group>

          <van-cell-group inset title="信息主题分布">
            <div class="dist" v-for="(n, k) in stats.by_topic" :key="k">
              <span class="dist-label">{{ k }}</span>
              <div class="dist-track"><div class="dist-fill green" :style="{ width: pct(n, stats.total) }"></div></div>
              <span class="dist-n">{{ n }}</span>
            </div>
          </van-cell-group>

          <van-cell-group inset title="状态分布">
            <div class="dist" v-for="(n, k) in stats.by_status" :key="k">
              <span class="dist-label">{{ k }}</span>
              <div class="dist-track"><div class="dist-fill orange" :style="{ width: pct(n, stats.total) }"></div></div>
              <span class="dist-n">{{ n }}</span>
            </div>
          </van-cell-group>

          <van-cell-group inset title="活跃提交人 TOP5">
            <van-cell v-for="(s, i) in stats.top_submitters" :key="s.name">
              <template #title>
                <span class="rank" :class="'rank' + (i + 1)">{{ i + 1 }}</span> {{ s.name }}
              </template>
              <template #value>{{ s.c }} 条</template>
            </van-cell>
          </van-cell-group>

          <van-cell-group inset title="热门线索 TOP5">
            <van-cell v-for="h in stats.hot" :key="h.id" :title="h.title" is-link
              :label="`👍 ${h.likes} · 👁 ${h.views}`" @click="$router.push(`/clue/${h.id}`)" />
          </van-cell-group>
        </div>
      </van-tab>

      <!-- 账号管理 -->
      <van-tab title="账号">
        <div class="panel">
          <div class="acct-btns">
            <van-button type="primary" icon="plus" @click="showAdd = true">分配新账号</van-button>
            <van-button icon="friends-o" :loading="importing" @click="pickImport">批量导入</van-button>
            <van-button plain icon="down" @click="downloadTemplate">下载模板</van-button>
          </div>
          <input ref="importInput" type="file" accept=".xlsx" hidden @change="doImport" />
          <van-cell-group v-for="u in users" :key="u.id" inset class="user-card">
            <van-cell :title="u.name" :label="`用户名：${u.username}`">
              <template #value>
                <van-tag v-for="r in u.role_names" :key="r" type="primary" plain size="medium">{{ r }}</van-tag>
              </template>
            </van-cell>
            <van-cell title="查看权限">
              <template #value>
                <van-tag v-for="p in u.perm_list" :key="p" type="warning" plain size="medium">{{ p }}</van-tag>
                <span v-if="!u.perm_list.length" class="noperm">仅"其他"类</span>
                <van-tag v-if="u.roles.includes('approver')" type="success" plain size="medium" style="margin-left:4px">
                  审批·{{ u.approve_scope || '未分配' }}
                </van-tag>
              </template>
            </van-cell>
            <van-cell>
              <template #title>
                <div class="user-ops">
                  <van-button size="mini" @click="editUser(u)">编辑</van-button>
                  <van-button size="mini" @click="resetPw(u)">重置密码</van-button>
                  <van-button v-if="u.id !== myId" size="mini" type="danger" plain @click="delUser(u)">删除</van-button>
                </div>
              </template>
            </van-cell>
          </van-cell-group>
        </div>
      </van-tab>

      <!-- 线索管理 -->
      <van-tab title="线索">
        <div class="panel">
          <van-button block type="primary" icon="down" :loading="exporting" @click="exportXlsx">导出全部线索（Excel）</van-button>
          <div v-for="c in clues" :key="c.id" class="clue-admin">
            <div class="ca-head" @click="$router.push(`/clue/${c.id}`)">
              <span class="ca-title">{{ c.title }}</span>
              <span class="ca-sub">{{ c.submitter_name }}</span>
            </div>
            <div class="ca-ops">
              <van-dropdown-menu>
                <van-dropdown-item :model-value="c.status" :options="statusOpts"
                  @change="v => setStatus(c, v)" />
              </van-dropdown-menu>
              <van-button size="mini" type="danger" plain @click="delClue(c)">删除</van-button>
            </div>
          </div>
        </div>
      </van-tab>

      <!-- 标签体系 -->
      <van-tab title="标签体系">
        <div class="panel" v-if="taxEdit">
          <van-notice-bar wrapable :scrollable="false"
            text="修改标签体系实时生效，仅影响后续提交和筛选；已有线索的旧标签保留不变。" />
          <template v-for="sec in taxSections" :key="sec.key">
            <van-cell-group inset :title="sec.title">
              <div class="tax-list">
                <van-tag v-for="(item, i) in getList(sec)" :key="item" size="large" closeable
                  :type="sec.key === 'depts' ? 'primary' : 'default'"
                  @close="removeItem(sec, i)">{{ item }}</van-tag>
                <van-tag size="large" type="primary" plain @click="addTarget = sec; newItem = ''; showAddItem = true">+ 添加</van-tag>
              </div>
            </van-cell-group>
          </template>
          <van-button block type="primary" :loading="savingTax" @click="saveTax" style="margin-top: 16px">
            保存标签体系
          </van-button>
        </div>
      </van-tab>

      <!-- 设置 -->
      <van-tab title="设置">
        <div class="panel">
          <van-cell-group inset title="外部 AI 服务">
            <van-cell title="启用外部 AI 推荐/识别" label="开启后，点击AI推荐时的线索标题与内容将发送至外部AI服务商（DeepSeek）。关闭时使用本地智能引擎，数据不出本机。">
              <template #right-icon>
                <van-switch :model-value="settings.ai_external_enabled" :loading="savingSetting"
                  @update:model-value="toggleAi" size="22" />
              </template>
            </van-cell>
            <van-cell v-if="!settings.ai_key_configured" title="API Key" value="未配置（需在服务器配置）" />
          </van-cell-group>
        </div>
      </van-tab>
    </van-tabs>

    <!-- 新增账号 -->
    <van-dialog v-model:show="showAdd" title="分配新账号" show-cancel-button @confirm="addUser">
      <van-field v-model="nu.username" label="用户名" placeholder="登录用户名" />
      <van-field v-model="nu.name" label="姓名" placeholder="真实姓名" />
      <van-field v-model="nu.password" label="初始密码" placeholder="登录密码" />
      <van-field label="角色">
        <template #input>
          <van-checkbox-group v-model="nu.roles" direction="horizontal">
            <van-checkbox name="submitter">提交人</van-checkbox>
            <van-checkbox name="viewer">查看人</van-checkbox>
            <van-checkbox name="approver">审批员</van-checkbox>
            <van-checkbox name="admin">管理员</van-checkbox>
          </van-checkbox-group>
        </template>
      </van-field>
      <van-field v-if="nu.roles.includes('approver')" label="审批范围">
        <template #input>
          <van-radio-group v-model="nu.approve_scope" direction="horizontal">
            <van-radio v-for="p in PERM_SCOPES" :key="p" :name="p" class="perm-check">{{ p }}</van-radio>
          </van-radio-group>
        </template>
      </van-field>
      <van-field label="查看权限" label-width="100%">
        <template #input>
          <div>
            <van-checkbox-group v-model="nu.perms" direction="horizontal">
              <van-checkbox v-for="p in PERM_SCOPES" :key="p" :name="p" class="perm-check">{{ p }}</van-checkbox>
            </van-checkbox-group>
            <p class="perm-tip">勾选后可查看对应类别的线索；"其他"类线索全员可见</p>
          </div>
        </template>
      </van-field>
    </van-dialog>

    <!-- 编辑角色与权限 -->
    <van-dialog v-model:show="showEdit" :title="`编辑：${editing?.name}`" show-cancel-button @confirm="saveRoles">
      <p class="dlg-label">角色</p>
      <van-checkbox-group v-model="editRoles" class="role-checks">
        <van-checkbox name="submitter">提交人</van-checkbox>
        <van-checkbox name="viewer">查看人</van-checkbox>
        <van-checkbox name="approver">审批员</van-checkbox>
        <van-checkbox name="admin">管理员</van-checkbox>
      </van-checkbox-group>
      <template v-if="editRoles.includes('approver')">
        <p class="dlg-label">审批范围</p>
        <van-radio-group v-model="editScope" class="role-checks">
          <van-radio v-for="p in PERM_SCOPES" :key="p" :name="p">{{ p }}</van-radio>
        </van-radio-group>
      </template>
      <p class="dlg-label">查看权限</p>
      <van-checkbox-group v-model="editPerms" class="role-checks">
        <van-checkbox v-for="p in PERM_SCOPES" :key="p" :name="p">{{ p }}</van-checkbox>
      </van-checkbox-group>
    </van-dialog>

    <!-- 导入结果 -->
    <van-dialog v-model:show="showImportResult" title="导入完成" confirm-button-text="知道了">
      <div class="import-result">
        <p>✅ 成功创建 {{ importResult.created.length }} 个账号<span v-if="importResult.created.length">：{{ importResult.created.join('、') }}</span></p>
        <p v-for="(s, i) in importResult.skipped" :key="i" class="skip">⚠️ {{ s }}</p>
      </div>
    </van-dialog>

    <!-- 重置密码 -->
    <van-dialog v-model:show="showReset" :title="`重置密码：${editing?.name}`" show-cancel-button @confirm="doResetPw">
      <van-field v-model="resetPwVal" label="新密码" placeholder="输入新密码" />
    </van-dialog>

    <!-- 添加标签项 -->
    <van-dialog v-model:show="showAddItem" :title="`添加${addTarget?.title || ''}`" show-cancel-button @confirm="addItem">
      <van-field v-model="newItem" placeholder="输入名称" />
    </van-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { showConfirmDialog, showSuccessToast, showToast } from 'vant'
import api from '../api'

const tab = ref(0)
const users = ref([])
const clues = ref([])
const stats = ref(null)
const taxEdit = ref(null)
const settings = ref({ ai_external_enabled: false, ai_key_configured: false })
const showAdd = ref(false)
const showEdit = ref(false)
const showReset = ref(false)
const editing = ref(null)
const editRoles = ref([])
const resetPwVal = ref('')
const exporting = ref(false)
const savingTax = ref(false)
const savingSetting = ref(false)
const showAddItem = ref(false)
const addTarget = ref(null)
const newItem = ref('')
const nu = reactive({ username: '', name: '', password: '', roles: ['submitter', 'viewer'], perms: ['结构件', '电子料', '化工料', 'IC'], approve_scope: '' })
const PERM_SCOPES = ['结构件', '电子料', '化工料', 'IC']
const editPerms = ref([])
const editScope = ref('')
const importing = ref(false)
const importInput = ref(null)
const showImportResult = ref(false)
const importResult = ref({ created: [], skipped: [] })
const statusOpts = ['待补充', '待核实', '已核实', '已归档'].map(s => ({ text: `状态：${s}`, value: s }))
const myId = computed(() => JSON.parse(localStorage.getItem('user') || '{}').id)

const taxSections = computed(() => {
  if (!taxEdit.value) return []
  const t = taxEdit.value
  const secs = [{ key: 'depts', title: '一级条线' }, { key: 'materials', title: '物料类别（原价）' }]
  for (const d of t.depts) {
    secs.push({ key: 'topics', dept: d, title: `信息主题（${d}）` })
    secs.push({ key: 'channels', dept: d, title: `获取方式（${d}）` })
  }
  return secs
})
const maxTrend = computed(() => Math.max(1, ...(stats.value?.trend.map(t => t.c) || [1])))

function getList(sec) {
  if (sec.key === 'topics' || sec.key === 'channels') return taxEdit.value[sec.key][sec.dept] || []
  return taxEdit.value[sec.key]
}
function removeItem(sec, i) { getList(sec).splice(i, 1) }
function addItem() {
  const v = newItem.value.trim()
  if (!v) return
  const list = getList(addTarget.value)
  if (!list.includes(v)) list.push(v)
}
function barH(n, max) { return Math.max(4, (n / max) * 80) + 'px' }
function pct(n, total) { return total ? Math.round((n / total) * 100) + '%' : '0%' }

async function load() {
  users.value = await api.get('/admin/users')
  const res = await api.get('/clues', { params: { sort: 'fresh' } })
  clues.value = res.items
}
async function loadStats() { stats.value = await api.get('/admin/stats') }
async function loadTax() { taxEdit.value = await api.get('/admin/taxonomy') }
async function loadSettings() { settings.value = await api.get('/admin/settings') }

watch(tab, v => {
  if (v === 0) loadStats()
  if (v === 1) load()
  if (v === 2) load()
  if (v === 3) loadTax()
  if (v === 4) loadSettings()
})

async function addUser() {
  await api.post('/admin/users', { ...nu })
  showSuccessToast('账号已分配')
  Object.assign(nu, { username: '', name: '', password: '', roles: ['submitter', 'viewer'], perms: [...PERM_SCOPES], approve_scope: '' })
  load()
}
function editUser(u) {
  editing.value = u
  editRoles.value = u.roles.split(',')
  editPerms.value = [...(u.perm_list || [])]
  editScope.value = u.approve_scope || ''
  showEdit.value = true
}
async function saveRoles() {
  await api.patch(`/admin/users/${editing.value.id}`, { roles: editRoles.value, perms: editPerms.value, approve_scope: editScope.value })
  showSuccessToast('已更新'); load()
}
function pickImport() { importInput.value?.click() }
async function doImport(e) {
  const f = e.target.files[0]
  e.target.value = ''
  if (!f) return
  importing.value = true
  try {
    const fd = new FormData()
    fd.append('file', f)
    importResult.value = await api.post('/admin/users/import', fd, { headers: { 'Content-Type': 'multipart/form-data' } })
    showImportResult.value = true
    load()
  } finally { importing.value = false }
}
async function downloadTemplate() {
  const token = localStorage.getItem('token')
  const res = await fetch('/api/admin/users/template', { headers: { Authorization: `Bearer ${token}` } })
  const blob = await res.blob()
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = '账号导入模板.xlsx'
  a.click()
}
function resetPw(u) { editing.value = u; resetPwVal.value = ''; showReset.value = true }
async function doResetPw() {
  if (!resetPwVal.value) return
  await api.patch(`/admin/users/${editing.value.id}`, { password: resetPwVal.value })
  showSuccessToast('密码已重置')
}
async function delUser(u) {
  await showConfirmDialog({ title: '删除账号', message: `确认删除 ${u.name} 的账号？其提交的线索将保留。` })
  await api.delete(`/admin/users/${u.id}`)
  load()
}
async function setStatus(c, v) {
  await api.patch(`/clues/${c.id}`, { status: v })
  c.status = v
  showSuccessToast('状态已更新')
}
async function delClue(c) {
  await showConfirmDialog({ title: '删除线索', message: `确认删除「${c.title}」？该操作不可恢复。` })
  await api.delete(`/clues/${c.id}`)
  load()
}
async function exportXlsx() {
  exporting.value = true
  try {
    const token = localStorage.getItem('token')
    const res = await fetch('/api/admin/export', { headers: { Authorization: `Bearer ${token}` } })
    const blob = await res.blob()
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = `线索池导出_${new Date().toISOString().slice(0, 10)}.xlsx`
    a.click()
    showSuccessToast('导出成功')
  } finally { exporting.value = false }
}
async function saveTax() {
  savingTax.value = true
  try {
    await api.put('/admin/taxonomy', taxEdit.value)
    showSuccessToast('标签体系已保存，实时生效')
  } finally { savingTax.value = false }
}
async function toggleAi(v) {
  if (v) {
    await showConfirmDialog({
      title: '启用外部 AI？',
      message: '启用后，使用 AI 推荐/识别时，线索的标题与内容将发送至外部 AI 服务商（DeepSeek）。请确认符合部门信息安全要求。',
    })
  }
  savingSetting.value = true
  try {
    await api.put('/admin/settings', { ai_external_enabled: v })
    settings.value.ai_external_enabled = v
    showToast(v ? '外部 AI 已启用' : '已切换回本地智能引擎')
  } finally { savingSetting.value = false }
}

onMounted(() => { load(); loadStats() })
</script>

<style scoped>
.panel { padding: 12px; }
.user-card { margin: 10px 0; }
.user-ops { display: flex; gap: 8px; }
.clue-admin { background: #fff; border-radius: 10px; margin: 10px 0; padding: 12px; }
.ca-head { display: flex; align-items: center; }
.ca-title { flex: 1; font-weight: 500; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.ca-sub { color: #969799; font-size: 12px; margin-left: 8px; }
.ca-ops { display: flex; align-items: center; gap: 10px; margin-top: 8px; }
.ca-ops .van-dropdown-menu { flex: 1; height: 32px; border-radius: 6px; }
.role-checks { padding: 4px 24px 16px; display: flex; flex-direction: column; gap: 12px; }
.dlg-label { padding: 16px 24px 4px; margin: 0; font-size: 13px; color: #969799; }
.acct-btns { display: flex; gap: 8px; }
.acct-btns .van-button { flex: 1; }
.noperm { color: #969799; font-size: 12px; }
.perm-check { margin-bottom: 6px; }
.perm-tip { font-size: 11px; color: #969799; margin: 6px 0 0; }
.import-result { padding: 8px 24px 16px; font-size: 13px; }
.import-result .skip { color: #ff976a; }
.tax-list { display: flex; flex-wrap: wrap; gap: 8px; padding: 12px 16px; }
/* 看板 */
.stat-cards { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; margin-bottom: 14px; }
.stat-card { background: #fff; border-radius: 10px; padding: 12px 0; text-align: center; box-shadow: 0 1px 4px rgba(0,0,0,.05); }
.stat-card b { display: block; font-size: 20px; color: #1989fa; }
.stat-card span { font-size: 11px; color: #969799; }
.trend { display: flex; align-items: flex-end; gap: 4px; padding: 12px 16px 8px; overflow-x: auto; }
.trend-col { display: flex; flex-direction: column; align-items: center; min-width: 26px; }
.trend-bar { width: 14px; background: linear-gradient(180deg, #39b9fa, #1989fa); border-radius: 3px 3px 0 0; }
.trend-n { font-size: 10px; color: #646566; }
.trend-d { font-size: 9px; color: #969799; }
.dist { display: flex; align-items: center; gap: 8px; padding: 8px 16px; }
.dist-label { width: 72px; font-size: 12px; color: #646566; flex-shrink: 0; }
.dist-track { flex: 1; height: 10px; background: #f2f3f5; border-radius: 5px; overflow: hidden; }
.dist-fill { height: 100%; border-radius: 5px; }
.dist-fill.blue { background: #1989fa; } .dist-fill.green { background: #07c160; } .dist-fill.orange { background: #ff976a; }
.dist-n { width: 28px; text-align: right; font-size: 12px; color: #969799; }
.rank { display: inline-block; width: 18px; height: 18px; line-height: 18px; text-align: center; border-radius: 4px; background: #f2f3f5; font-size: 11px; margin-right: 6px; }
.rank1 { background: #ffe1ba; color: #ed6a0c; } .rank2 { background: #e1ebff; color: #1989fa; } .rank3 { background: #dcf5e7; color: #07c160; }
</style>
