<template>
  <div class="page">
    <van-nav-bar title="提交线索" />

    <van-tabs v-model:active="mode" sticky animated>
      <!-- ============ 快速录入 ============ -->
      <van-tab title="⚡ 快速录入">
        <div class="quick">
          <p class="hint">时间紧急？30 秒先记下，回头再补充完整</p>

          <van-field v-model="quick.title" label="标题" placeholder="一句话说清这条线索" required />

          <div class="voice-box">
            <van-field v-model="quick.content" type="textarea" rows="4" autosize
              placeholder="输入内容，或点击下方按钮语音输入 / 拍照识别" />
            <div class="input-tools">
              <div class="tool" :class="{ recording }" @click="toggleVoice">
                <van-icon :name="recording ? 'stop-circle-o' : 'volume-o'" size="22" />
                <span>{{ recording ? '停止' : '语音输入' }}</span>
              </div>
              <label class="tool">
                <van-icon name="photograph" size="22" />
                <span>拍照/截图</span>
                <input type="file" accept="image/*" capture="environment" hidden @change="onPhoto" />
              </label>
            </div>
            <p v-if="!voiceSupported" class="voice-tip">当前浏览器不支持语音输入，请手动输入或使用拍照</p>
          </div>

          <div v-if="ocrLoading" class="ocr-loading"><van-loading size="20" /> 正在识别图片文字…</div>

          <div v-if="images.length" class="imgs">
            <div v-for="(img, i) in images" :key="i" class="img-wrap">
              <img :src="img" />
              <van-icon name="cross" class="del" @click="images.splice(i, 1)" />
            </div>
          </div>

          <!-- 快速录入也可以打标签 -->
          <div class="quick-tags">
            <div class="qt-head">
              <span class="qt-title">关键词标签（可选）</span>
              <van-button size="mini" plain hairline type="primary" icon="magic" :loading="aiLoading"
                @click="aiSuggest(true)">智能推荐</van-button>
            </div>
            <div class="opts">
              <van-tag v-for="(k, i) in quick.keywords" :key="k" size="large" type="primary" plain closeable
                @close="quick.keywords.splice(i, 1)">{{ k }}</van-tag>
              <van-tag size="large" plain @click="kwTarget = 'quick'; showKwInput = true">+ 添加</van-tag>
            </div>
          </div>

          <van-button block type="primary" round class="submit-btn" :loading="submitting" @click="quickSubmit">
            快速提交（稍后补充）
          </van-button>
          <van-button block plain type="primary" round @click="quickToFull">信息齐全？转为完整录入</van-button>
        </div>
      </van-tab>

      <!-- ============ 完整录入 ============ -->
      <van-tab title="📋 完整录入">
        <van-form @submit="fullSubmit" class="full">
          <van-field v-model="form.title" label="标题" required placeholder="线索标题"
            :rules="[{ required: true, message: '请填写标题' }]" />
          <van-field v-model="form.content" label="内容" type="textarea" rows="4" autosize required
            placeholder="线索详细内容：谁、何时、何地、何事" :rules="[{ required: true, message: '请填写内容' }]" />
          <van-field v-model="form.source" label="来源" required placeholder="来源身份，如：某供应商销售经理"
            :rules="[{ required: true, message: '请填写来源' }]" />
          <van-field v-model="form.scene" label="场景" required placeholder="获取场景/地点，如：供应商工厂"
            :rules="[{ required: true, message: '请填写场景' }]" />
          <van-field v-model="form.acquired_at" label="获取时间" required placeholder="如 2026-11-07 14:00"
            :rules="[{ required: true, message: '请填写获取时间' }]" />

          <!-- 常用标签组合 -->
          <div v-if="presets.length" class="preset-bar">
            <span class="preset-label">常用组合：</span>
            <van-tag v-for="p in presets" :key="p.id" size="large" color="#eef7ff" text-color="#1989fa"
              @click="applyPreset(p)">{{ p.name }}</van-tag>
          </div>

          <!-- 条线（可多选） -->
          <van-field label="所属条线" required>
            <template #input>
              <div class="opts">
                <van-tag v-for="d in tax.depts" :key="d" size="large"
                  :type="form.depts.includes(d) ? 'primary' : 'default'"
                  @click="toggleDept(d)">{{ d }}</van-tag>
              </div>
            </template>
          </van-field>

          <!-- 物料类别（选了原价才出现） -->
          <van-field v-if="form.depts.includes('原价')" label="物料类别" required>
            <template #input>
              <div class="opts">
                <van-tag v-for="m in tax.materials" :key="m" size="large"
                  :type="form.material === m ? 'primary' : 'default'" @click="form.material = m">{{ m }}</van-tag>
              </div>
            </template>
          </van-field>

          <!-- 信息主题（按所选条线联动，单选） -->
          <van-field v-if="form.depts.length" label="信息主题" required>
            <template #input>
              <div>
                <template v-for="d in form.depts" :key="d">
                  <p v-if="form.depts.length > 1" class="topic-group">{{ d }}条线</p>
                  <div class="opts">
                    <van-tag v-for="t in tax.topics[d] || []" :key="t" size="large"
                      :type="form.category === t ? 'primary' : 'default'" @click="form.category = t">{{ t }}</van-tag>
                  </div>
                </template>
              </div>
            </template>
          </van-field>

          <!-- 获取方式（按条线联动，单选） -->
          <van-field v-if="form.depts.length" label="获取方式" required>
            <template #input>
              <div class="opts">
                <van-tag v-for="c in channelOptions" :key="c" size="large"
                  :type="form.channel === c ? 'primary' : 'default'" @click="form.channel = c">{{ c }}</van-tag>
              </div>
            </template>
          </van-field>

          <van-field label="可信度" required>
            <template #input>
              <van-radio-group v-model="form.credibility" direction="horizontal">
                <van-radio v-for="c in credibility" :key="c" :name="c">{{ c }}</van-radio>
              </van-radio-group>
            </template>
          </van-field>

          <van-field label="关键词标签">
            <template #input>
              <div>
                <div class="opts kws">
                  <van-tag v-for="(k, i) in form.keywords" :key="k" size="large" type="primary" plain closeable
                    @close="form.keywords.splice(i, 1)">{{ k }}</van-tag>
                  <van-tag size="large" plain @click="kwTarget = 'form'; showKwInput = true">+ 添加</van-tag>
                </div>
                <van-button size="small" plain hairline type="primary" icon="magic" :loading="aiLoading"
                  class="ai-btn" @click.prevent="aiSuggest(false)">
                  {{ meta.ai_enabled ? 'AI 推荐（外部AI）' : '智能推荐（本地引擎·数据不外传）' }}
                </van-button>
              </div>
            </template>
          </van-field>

          <van-field label="图片附件">
            <template #input>
              <div class="imgs">
                <div v-for="(img, i) in images" :key="i" class="img-wrap">
                  <img :src="img" />
                  <van-icon name="cross" class="del" @click="images.splice(i, 1)" />
                </div>
                <label class="img-add">
                  <van-icon name="plus" size="24" />
                  <input type="file" accept="image/*" multiple hidden @change="onPhoto" />
                </label>
              </div>
            </template>
          </van-field>

          <van-button block type="primary" round native-type="submit" class="submit-btn" :loading="submitting">
            提交完整线索
          </van-button>
          <van-button block plain round icon="star-o" @click.prevent="showSavePreset = true"
            :disabled="!form.depts.length || !form.category">
            将当前分类组合存为常用组合
          </van-button>
        </van-form>
      </van-tab>
    </van-tabs>

    <!-- 保存标签组合 -->
    <van-dialog v-model:show="showSavePreset" title="保存常用组合" show-cancel-button @confirm="savePreset">
      <div class="preset-preview">
        <p>{{ [...form.depts, form.material, form.category, form.channel].filter(Boolean).join(' → ') }}</p>
      </div>
      <van-field v-model="presetName" placeholder="为组合起名，如：供应商出差-结构件" />
    </van-dialog>

    <van-dialog v-model:show="showKwInput" title="添加关键词" show-cancel-button @confirm="addKw">
      <van-field v-model="newKw" placeholder="如：供应商名、物料型号、事件名" />
    </van-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { showToast, showSuccessToast } from 'vant'
import api from '../api'

const router = useRouter()
const mode = ref(0)
const meta = ref({ taxonomy: { depts: [], materials: [], topics: {}, channels: {} }, credibility: [], ai_enabled: false })
const tax = computed(() => meta.value.taxonomy)
const credibility = computed(() => meta.value.credibility)
const submitting = ref(false)
const aiLoading = ref(false)
const ocrLoading = ref(false)
const images = ref([])
const showKwInput = ref(false)
const newKw = ref('')
const kwTarget = ref('form')
const presets = ref([])
const showSavePreset = ref(false)
const presetName = ref('')

function applyPreset(p) {
  form.depts = [...p.depts]
  form.material = p.material || ''
  form.category = p.category || ''
  form.channel = p.channel || ''
  if (p.keywords?.length) {
    const merged = new Set([...form.keywords, ...p.keywords])
    form.keywords = [...merged].slice(0, 8)
  }
  showSuccessToast(`已应用组合「${p.name}」`)
}
async function savePreset() {
  if (!presetName.value.trim()) { showToast('请为组合命名'); return }
  await api.post('/presets', {
    name: presetName.value.trim(), depts: form.depts, material: form.material,
    category: form.category, channel: form.channel, keywords: [],
  })
  presetName.value = ''
  presets.value = await api.get('/presets')
  showSuccessToast('组合已保存，下次一键套用')
}
async function loadPresets() { presets.value = await api.get('/presets') }

const quick = reactive({ title: '', content: '', keywords: [] })
const form = reactive({
  title: '', content: '', source: '', scene: '', acquired_at: '',
  depts: [], material: '', category: '', channel: '', credibility: '中', keywords: [],
})

const channelOptions = computed(() => {
  const ch = tax.value.channels || {}
  const merged = []
  for (const d of form.depts) for (const c of ch[d] || []) if (!merged.includes(c)) merged.push(c)
  return merged
})

function toggleDept(d) {
  const i = form.depts.indexOf(d)
  if (i >= 0) form.depts.splice(i, 1); else form.depts.push(d)
  // 取消原价时清掉物料
  if (!form.depts.includes('原价')) form.material = ''
  // 主题不在当前可选范围时清空
  const valid = form.depts.flatMap(x => tax.value.topics[x] || [])
  if (form.category && !valid.includes(form.category)) form.category = ''
  if (form.channel && !channelOptions.value.includes(form.channel)) form.channel = ''
}

// ---------- 语音输入 ----------
const recording = ref(false)
const voiceSupported = 'webkitSpeechRecognition' in window || 'SpeechRecognition' in window
let recog = null
function toggleVoice() {
  if (!voiceSupported) return
  if (recording.value) { recog?.stop(); return }
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition
  recog = new SR()
  recog.lang = 'zh-CN'
  recog.continuous = true
  recog.interimResults = true
  recog.onresult = e => {
    let text = ''
    for (const r of e.results) if (r.isFinal) text += r[0].transcript
    if (text) quick.content = (quick.content + text).trim()
  }
  recog.onend = () => { recording.value = false }
  recog.onerror = () => { recording.value = false; showToast('语音识别不可用，请手动输入') }
  recog.start()
  recording.value = true
}

// ---------- 拍照 + OCR ----------
async function onPhoto(e) {
  const files = [...e.target.files]
  e.target.value = ''
  for (const f of files) {
    const fd = new FormData()
    fd.append('file', f)
    const up = await api.post('/upload', fd, { headers: { 'Content-Type': 'multipart/form-data' } })
    images.value.push(up.url)
    if (meta.value.ai_enabled) {
      ocrLoading.value = true
      try {
        const fd2 = new FormData()
        fd2.append('file', f)
        const ocr = await api.post('/ai/ocr', fd2, { headers: { 'Content-Type': 'multipart/form-data' } })
        if (ocr.text) {
          const target = mode.value === 0 ? quick : form
          target.content = (target.content + '\n' + ocr.text).trim()
          showSuccessToast('已识别图片文字')
        }
      } finally { ocrLoading.value = false }
    }
  }
}

// ---------- 智能推荐 ----------
async function aiSuggest(isQuick) {
  const target = isQuick ? quick : form
  if (!target.title && !target.content) { showToast('请先填写标题或内容'); return }
  aiLoading.value = true
  try {
    const res = await api.post('/ai/suggest', { title: target.title, content: target.content })
    const merged = new Set([...target.keywords, ...(res.tags || [])])
    target.keywords = [...merged].slice(0, 8)
    if (!isQuick) {
      if (res.depts?.length) form.depts = res.depts.filter(d => tax.value.depts.includes(d))
      if (res.category) form.category = res.category
      if (res.material && form.depts.includes('原价')) form.material = res.material
    }
    showSuccessToast(res.ai ? 'AI 已推荐，可手动调整' : '本地引擎已推荐，可手动调整')
  } finally { aiLoading.value = false }
}

function addKw() {
  const k = newKw.value.trim()
  const target = kwTarget.value === 'quick' ? quick : form
  if (k && !target.keywords.includes(k)) target.keywords.push(k)
  newKw.value = ''
}

// ---------- 提交 ----------
async function quickSubmit() {
  if (!quick.title.trim()) { showToast('请填写标题'); return }
  submitting.value = true
  try {
    const res = await api.post('/clues', {
      title: quick.title.trim(), content: quick.content.trim(),
      status: '待补充', images: images.value, keywords: quick.keywords, depts: [],
    })
    showSuccessToast('已快速提交，可稍后补充')
    router.push(`/clue/${res.id}`)
  } finally { submitting.value = false }
}

function quickToFull() {
  form.title = quick.title
  form.content = quick.content
  form.keywords = [...quick.keywords]
  mode.value = 1
}

async function fullSubmit() {
  if (!form.depts.length) { showToast('请选择所属条线'); return }
  if (form.depts.includes('原价') && !form.material) { showToast('请选择物料类别'); return }
  if (!form.category) { showToast('请选择信息主题'); return }
  if (!form.channel) { showToast('请选择获取方式'); return }
  submitting.value = true
  try {
    const res = await api.post('/clues', { ...form, images: images.value, status: '待核实' })
    showSuccessToast('线索提交成功')
    router.push(`/clue/${res.id}`)
  } finally { submitting.value = false }
}

onMounted(async () => {
  meta.value = await api.get('/meta')
  const d = new Date()
  const p = n => String(n).padStart(2, '0')
  form.acquired_at = `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`
  loadPresets()
})
</script>

<style scoped>
.quick, .full { padding: 16px; }
.hint { color: #ff976a; font-size: 13px; margin: 0 0 12px; }
.voice-box { position: relative; background: #fff; border-radius: 8px; margin-top: 12px; }
.input-tools { display: flex; gap: 16px; padding: 8px 16px 12px; }
.tool { display: flex; align-items: center; gap: 4px; color: #1989fa; font-size: 13px; padding: 6px 12px; border: 1px dashed #1989fa; border-radius: 16px; }
.tool.recording { color: #ee0a24; border-color: #ee0a24; animation: pulse 1s infinite; }
@keyframes pulse { 50% { opacity: .5; } }
.voice-tip { color: #969799; font-size: 12px; padding: 0 16px 10px; margin: 0; }
.ocr-loading { display: flex; align-items: center; gap: 8px; color: #1989fa; font-size: 13px; padding: 8px 0; }
.imgs { display: flex; gap: 8px; flex-wrap: wrap; margin: 12px 0; }
.img-wrap { position: relative; }
.img-wrap img { width: 80px; height: 80px; object-fit: cover; border-radius: 8px; }
.img-wrap .del { position: absolute; top: -6px; right: -6px; background: #ee0a24; color: #fff; border-radius: 50%; padding: 2px; font-size: 12px; }
.img-add { width: 80px; height: 80px; border: 1px dashed #dcdee0; border-radius: 8px; display: flex; align-items: center; justify-content: center; color: #969799; }
.submit-btn { margin: 16px 0 12px; }
.opts { display: flex; flex-wrap: wrap; gap: 8px; }
.kws { margin-bottom: 10px; }
.ai-btn { margin-top: 4px; }
.quick-tags { background: #fff; border-radius: 8px; padding: 12px 16px; margin-top: 12px; }
.qt-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
.qt-title { font-size: 14px; color: #646566; }
.topic-group { font-size: 12px; color: #969799; margin: 8px 0 6px; }
.preset-bar { display: flex; align-items: center; flex-wrap: wrap; gap: 8px; background: #fff; border-radius: 8px; padding: 12px 16px; margin-bottom: 12px; }
.preset-label { font-size: 13px; color: #969799; }
.preset-preview { padding: 12px 24px 0; color: #576b95; font-size: 13px; }
</style>
