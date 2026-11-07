<template>
  <div class="page">
    <van-nav-bar title="线索详情" left-arrow @click-left="$router.back()">
      <template #right>
        <van-icon v-if="canEdit" name="edit" size="20" @click="openEdit" />
      </template>
    </van-nav-bar>

    <div v-if="clue" class="detail">
      <div class="head">
        <van-tag v-for="d in clue.depts" :key="d" :type="d === '原价' ? 'warning' : 'primary'" plain size="large">{{ d }}</van-tag>
        <van-tag v-if="clue.material" type="warning" plain size="large">{{ clue.material }}</van-tag>
        <van-tag v-if="clue.category" size="large" color="#f2f6fc" text-color="#576b95">{{ clue.category }}</van-tag>
        <van-tag :type="statusType(clue.status)" size="large">{{ clue.status }}</van-tag>
        <van-tag :type="approvalType(clue.approval)" size="large" plain>{{ clue.approval }}</van-tag>
      </div>
      <h2>{{ clue.title }}</h2>
      <p class="content">{{ clue.content || '（暂无详细内容，待补充）' }}</p>

      <van-image-preview v-model:show="showPreview" :images="previewImgs" :start-position="previewIdx" />
      <div v-if="clue.images.length" class="imgs">
        <img v-for="(img, i) in clue.images" :key="i" :src="img" @click="preview(i)" />
      </div>

      <van-cell-group inset class="info">
        <van-cell title="来源身份" :value="clue.source || '未填写'" />
        <van-cell title="获取场景/地点" :value="clue.scene || '未填写'" />
        <van-cell title="获取时间" :value="clue.acquired_at || '未填写'" />
        <van-cell title="获取方式" :value="clue.channel || '未填写'" />
        <van-cell title="可信度">
          <template #value><span :class="'cred-' + clue.credibility">{{ clue.credibility }}</span></template>
        </van-cell>
        <van-cell title="提交人">
          <template #value>
            {{ clue.submitter_name }}
            <van-button v-if="clue.submitter_id !== userId" size="mini" plain type="primary" class="follow-btn"
              @click="follow('submitter', clue.submitter_id)">
              {{ followedSubmitter ? '已关注' : '+ 关注TA' }}
            </van-button>
          </template>
        </van-cell>
        <van-cell v-if="clue.category" title="信息主题">
          <template #value>
            {{ clue.category }}
            <van-button size="mini" plain type="primary" class="follow-btn" @click="follow('category', clue.category)">
              {{ followedCategory ? '已关注' : '+ 关注主题' }}
            </van-button>
          </template>
        </van-cell>
        <van-cell title="提交时间" :value="clue.created_at?.replace('T', ' ')" />
      </van-cell-group>

      <div class="kws">
        <van-tag v-for="k in clue.keywords" :key="k" size="medium" color="#f2f6fc" text-color="#576b95"># {{ k }}</van-tag>
      </div>

      <!-- 仅自己可见的个人标签 -->
      <van-cell-group inset class="mytags">
        <van-cell title="我的私人标签" label="仅自己可见，可用于个人归类检索" />
        <div class="tag-list">
          <van-tag v-for="t in clue.my_tags" :key="t" size="large" type="warning" plain closeable
            @close="removeTag(t)">{{ t }}</van-tag>
          <van-tag size="large" type="primary" plain @click="showTagInput = true">+ 添加</van-tag>
        </div>
      </van-cell-group>

      <div class="actions">
        <div class="act" :class="{ on: clue.liked }" @click="like">
          <van-icon :name="clue.liked ? 'good-job' : 'good-job-o'" size="24" />
          <span>{{ clue.likes || '点赞' }}</span>
        </div>
        <div class="act" :class="{ on: clue.favorited }" @click="fav">
          <van-icon :name="clue.favorited ? 'star' : 'star-o'" size="24" />
          <span>{{ clue.favorited ? '已收藏' : '收藏' }}</span>
        </div>
        <div class="act"><van-icon name="eye-o" size="24" /><span>{{ clue.views }}</span></div>
      </div>

      <!-- 审批区 -->
      <van-cell-group v-if="clue.approval !== '待审批' || clue.can_approve" inset class="approval">
        <van-cell title="审批状态">
          <template #value>
            <van-tag :type="approvalType(clue.approval)">{{ clue.approval }}</van-tag>
          </template>
        </van-cell>
        <van-cell v-if="clue.approved_by" title="审批人" :value="`${clue.approved_by} · ${(clue.approved_at || '').replace('T', ' ')}`" />
        <van-cell v-if="clue.approval_comment" title="审批意见" :value="clue.approval_comment" />
        <div v-if="clue.can_approve" class="approve-ops">
          <van-button type="success" size="small" icon="passed" @click="approve('pass')">通过</van-button>
          <van-button type="danger" size="small" plain icon="close" @click="approve('reject')">驳回</van-button>
          <van-button v-if="clue.approval !== '待审批'" size="small" plain @click="approve('reset')">撤销审批</van-button>
        </div>
      </van-cell-group>
    </div>

    <!-- 编辑/补充弹层 -->
    <van-popup v-model:show="editMode" position="bottom" round :style="{ height: '92%' }">
      <div class="edit-panel">
        <h3>{{ clue?.status === '待补充' ? '补充完整线索' : '编辑线索' }}</h3>
        <van-form @submit="saveEdit">
          <van-field v-model="edit.title" label="标题" required placeholder="线索标题" />
          <van-field v-model="edit.content" label="内容" type="textarea" rows="4" autosize placeholder="线索详细内容" />
          <van-field v-model="edit.source" label="来源" placeholder="来源身份" />
          <van-field v-model="edit.scene" label="场景" placeholder="获取场景/地点" />
          <van-field v-model="edit.acquired_at" label="获取时间" placeholder="如 2026-11-07 下午" />
          <van-field label="条线">
            <template #input>
              <div class="opts">
                <van-tag v-for="d in tax.depts" :key="d" size="large"
                  :type="edit.depts.includes(d) ? 'primary' : 'default'" @click="toggleEditDept(d)">{{ d }}</van-tag>
              </div>
            </template>
          </van-field>
          <van-field v-if="edit.depts.includes('原价')" label="物料类别">
            <template #input>
              <div class="opts">
                <van-tag v-for="m in tax.materials" :key="m" size="large"
                  :type="edit.material === m ? 'primary' : 'default'" @click="edit.material = m">{{ m }}</van-tag>
              </div>
            </template>
          </van-field>
          <van-field v-if="edit.depts.length" label="信息主题">
            <template #input>
              <div class="opts">
                <van-tag v-for="t in editTopics" :key="t" size="large"
                  :type="edit.category === t ? 'primary' : 'default'" @click="edit.category = t">{{ t }}</van-tag>
              </div>
            </template>
          </van-field>
          <van-field v-if="edit.depts.length" label="获取方式">
            <template #input>
              <div class="opts">
                <van-tag v-for="c in editChannels" :key="c" size="large"
                  :type="edit.channel === c ? 'primary' : 'default'" @click="edit.channel = c">{{ c }}</van-tag>
              </div>
            </template>
          </van-field>
          <van-field label="可信度">
            <template #input>
              <van-radio-group v-model="edit.credibility" direction="horizontal">
                <van-radio v-for="c in meta.credibility" :key="c" :name="c">{{ c }}</van-radio>
              </van-radio-group>
            </template>
          </van-field>
          <van-field v-model="editKw" label="关键词" placeholder="逗号分隔，如：竞品A,降价" />
          <van-button block type="primary" native-type="submit" :loading="saving" style="margin-top: 12px">保 存</van-button>
        </van-form>
      </div>
    </van-popup>

    <!-- 添加个人标签 -->
    <van-dialog v-model:show="showTagInput" title="添加私人标签" show-cancel-button @confirm="addTag">
      <van-field v-model="newTag" placeholder="如：重点跟进、再核实" />
    </van-dialog>

    <!-- 关注方式选择 -->
    <van-dialog v-model:show="showFollowOpt" title="关注设置" :message="followMsg"
      show-cancel-button cancel-button-text="悄悄关注（隐藏）" confirm-button-text="公开关注"
      @confirm="doFollow(true)" @cancel="doFollow(false)" />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { showToast } from 'vant'
import api from '../api'

const route = useRoute()
const clue = ref(null)
const meta = ref({ taxonomy: { depts: [], materials: [], topics: {}, channels: {} }, credibility: [] })
const tax = computed(() => meta.value.taxonomy)
const follows = ref([])
const editMode = ref(false)
const saving = ref(false)
const edit = ref({ depts: [] })
const editKw = ref('')
const showTagInput = ref(false)
const newTag = ref('')
const showFollowOpt = ref(false)
const showPreview = ref(false)
const previewIdx = ref(0)
let pendingFollow = null

const userId = computed(() => JSON.parse(localStorage.getItem('user') || '{}').id)
const canEdit = computed(() => clue.value && (clue.value.submitter_id === userId.value || isAdmin()))
const previewImgs = computed(() => clue.value?.images || [])
const followMsg = computed(() => '公开关注后，对方和同事们可以看到你的关注；选择隐藏则只有自己可见。')
const followedSubmitter = computed(() =>
  follows.value.some(f => f.target_type === 'submitter' && f.target_value === String(clue.value?.submitter_id)))
const followedCategory = computed(() =>
  follows.value.some(f => f.target_type === 'category' && f.target_value === clue.value?.category))
const editTopics = computed(() => [...new Set((edit.value.depts || []).flatMap(d => tax.value.topics[d] || []))])
const editChannels = computed(() => [...new Set((edit.value.depts || []).flatMap(d => tax.value.channels[d] || []))])

function isAdmin() { return JSON.parse(localStorage.getItem('user') || '{}').roles?.includes('admin') }
function statusType(s) { return { '待补充': 'danger', '待核实': 'primary', '已核实': 'success', '已归档': 'default' }[s] || 'default' }
function approvalType(a) { return { '待审批': 'warning', '已通过': 'success', '已驳回': 'danger' }[a] || 'default' }
async function approve(action) {
  let comment = ''
  if (action === 'reject') {
    comment = prompt('请输入驳回意见（可留空）') || ''
  }
  const res = await api.post(`/clues/${clue.value.id}/approve`, { action, comment })
  clue.value = { ...clue.value, ...res }
  showToast({ type: 'success', message: action === 'pass' ? '已通过' : action === 'reject' ? '已驳回' : '已撤销' })
}
function preview(i) { previewIdx.value = i; showPreview.value = true }
function toggleEditDept(d) {
  const i = edit.value.depts.indexOf(d)
  if (i >= 0) edit.value.depts.splice(i, 1); else edit.value.depts.push(d)
}

async function load() {
  clue.value = await api.get(`/clues/${route.params.id}`)
  const f = await api.get('/follows')
  follows.value = f.follows
}

async function like() {
  const res = await api.post(`/clues/${clue.value.id}/like`)
  clue.value.liked = res.liked; clue.value.likes = res.likes
}
async function fav() {
  const res = await api.post(`/clues/${clue.value.id}/favorite`)
  clue.value.favorited = res.favorited
  showToast(res.favorited ? '已收藏' : '已取消收藏')
}
function follow(type, value) {
  pendingFollow = { type, value }
  showFollowOpt.value = true
}
async function doFollow(isPublic) {
  const { type, value } = pendingFollow
  await api.post('/follows', { target_type: type, target_value: value, is_public: isPublic })
  showToast(isPublic ? '已公开关注' : '已悄悄关注')
  load()
}
async function addTag() {
  if (!newTag.value.trim()) return
  const res = await api.post(`/clues/${clue.value.id}/my-tags`, { tag: newTag.value.trim() })
  clue.value.my_tags = res.my_tags
  newTag.value = ''
}
async function removeTag(tag) {
  await api.delete(`/clues/${clue.value.id}/my-tags`, { params: { tag } })
  clue.value.my_tags = clue.value.my_tags.filter(t => t !== tag)
}
function openEdit() {
  edit.value = {
    title: clue.value.title, content: clue.value.content, source: clue.value.source,
    scene: clue.value.scene, acquired_at: clue.value.acquired_at,
    depts: [...(clue.value.depts || [])], material: clue.value.material || '',
    category: clue.value.category || '', channel: clue.value.channel || '',
    credibility: clue.value.credibility,
  }
  editKw.value = (clue.value.keywords || []).join(',')
  editMode.value = true
}
async function saveEdit() {
  saving.value = true
  try {
    const body = { ...edit.value, keywords: editKw.value.split(/[,，]/).map(s => s.trim()).filter(Boolean) }
    clue.value = await api.patch(`/clues/${clue.value.id}`, body)
    showToast({ type: 'success', message: '已保存' })
    editMode.value = false
  } finally { saving.value = false }
}

onMounted(async () => {
  meta.value = await api.get('/meta')
  await load()
  if (clue.value.status === '待补充' && clue.value.submitter_id === userId.value) openEdit()
})
</script>

<style scoped>
.detail { padding: 16px; }
.head { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.cred-高 { color: #07c160; } .cred-中 { color: #ff976a; } .cred-低 { color: #969799; }
h2 { margin: 12px 0 8px; font-size: 20px; }
.content { color: #323233; line-height: 1.7; white-space: pre-wrap; }
.imgs { display: flex; gap: 8px; flex-wrap: wrap; margin: 12px 0; }
.imgs img { width: 100px; height: 100px; object-fit: cover; border-radius: 8px; }
.info { margin: 12px 0; }
.follow-btn { margin-left: 8px; }
.kws { display: flex; flex-wrap: wrap; gap: 6px; margin: 12px 0; }
.mytags { margin-bottom: 12px; }
.tag-list { display: flex; flex-wrap: wrap; gap: 8px; padding: 0 16px 16px; }
.actions { display: flex; justify-content: space-around; background: #fff; border-radius: 12px; padding: 14px 0; }
.act { display: flex; flex-direction: column; align-items: center; gap: 4px; color: #646566; font-size: 12px; }
.act.on { color: #ee0a24; }
.approval { margin-top: 12px; }
.approve-ops { display: flex; gap: 10px; padding: 12px 16px; }
.edit-panel { padding: 20px 16px 30px; overflow-y: auto; height: 100%; box-sizing: border-box; }
.edit-panel h3 { margin-top: 0; }
.opts { display: flex; flex-wrap: wrap; gap: 8px; }
</style>
