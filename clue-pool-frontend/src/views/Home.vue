<template>
  <div class="page">
    <div class="hero">
      <div class="hero-title">🔍 线索池 <span class="hero-dept">原价中心 · SCC</span></div>
      <div class="hero-sub">广泛收集 · 按需取用 · 持续深挖</div>
    </div>
    <van-sticky>
      <div class="topbar">
        <van-search v-model="kw" placeholder="搜索标题 / 内容 / 关键词" shape="round" @search="load" @clear="load" />
        <div class="filter-btn" @click="showFilter = true"><van-icon name="filter-o" size="22" /><span>筛选</span></div>
      </div>
      <van-tabs v-model:active="sort" @change="load" sticky offset-top="54" swipe-threshold="5">
        <van-tab name="fresh" title="最新" />
        <van-tab name="hot" title="热门" />
        <van-tab name="views" title="阅读" />
        <van-tab name="likes" title="点赞" />
      </van-tabs>
      <div class="quick-filter">
        <van-checkbox v-model="onlyFollowing" shape="square" icon-size="16px" @change="load">只看我关注的</van-checkbox>
        <van-tag v-if="hasFilter" type="primary" closeable @close="clearFilter">已设筛选</van-tag>
      </div>
    </van-sticky>

    <van-pull-refresh v-model="refreshing" @refresh="load">
      <van-list v-model:loading="loading" :finished="true" finished-text="没有更多了">
        <div v-for="c in items" :key="c.id" class="clue-card" @click="goDetail(c.id)">
          <div class="card-head">
            <van-tag v-for="d in c.depts" :key="d" :type="d === '原价' ? 'warning' : 'primary'" plain>{{ d }}</van-tag>
            <van-tag v-if="c.material" type="warning" plain>{{ c.material }}</van-tag>
            <van-tag v-if="c.category" color="#f2f6fc" text-color="#576b95">{{ c.category }}</van-tag>
            <van-tag v-if="c.status === '待补充'" type="danger">待补充</van-tag>
            <van-tag v-if="c.approval === '待审批'" color="#fff7e8" text-color="#ed6a0c">待审批</van-tag>
            <van-tag v-else-if="c.approval === '已通过'" color="#e8f8ef" text-color="#07c160">已通过</van-tag>
            <van-tag v-else-if="c.approval === '已驳回'" color="#fdeeee" text-color="#ee0a24">已驳回</van-tag>
            <span class="cred" :class="'cred-' + c.credibility">可信度·{{ c.credibility }}</span>
          </div>
          <h3 class="card-title">{{ c.title }}</h3>
          <p class="card-content">{{ c.content || '（暂无详细内容，待补充）' }}</p>
          <div class="card-kws">
            <van-tag v-for="k in c.keywords" :key="k" size="medium" color="#f2f6fc" text-color="#576b95"># {{ k }}</van-tag>
          </div>
          <div class="card-foot">
            <img v-if="c.submitter_avatar" :src="c.submitter_avatar" class="mini-avatar" />
            <span class="submitter">{{ c.submitter_name }}</span>
            <span class="time">{{ fmtTime(c.created_at) }}</span>
            <div class="stats">
              <span @click.stop="toggleLike(c)" :class="{ liked: c.liked }">
                <van-icon :name="c.liked ? 'good-job' : 'good-job-o'" /> {{ c.likes }}
              </span>
              <span><van-icon name="eye-o" /> {{ c.views }}</span>
            </div>
          </div>
        </div>
        <van-empty v-if="!items.length && !loading" description="暂无线索，快去提交第一条吧" />
      </van-list>
    </van-pull-refresh>

    <!-- 筛选面板 -->
    <van-popup v-model:show="showFilter" position="bottom" round :style="{ maxHeight: '82%' }">
      <div class="filter-panel">
        <h3>组合筛选</h3>
        <div class="fg"><label>所属条线</label>
          <div class="opts">
            <van-tag v-for="d in tax.depts" :key="d" size="large"
              :type="filter.dept === d ? 'primary' : 'default'" @click="toggle('dept', d)">{{ d }}</van-tag>
          </div>
        </div>
        <div class="fg" v-if="!filter.dept || filter.dept === '原价'"><label>物料类别（原价）</label>
          <div class="opts">
            <van-tag v-for="m in tax.materials" :key="m" size="large"
              :type="filter.material === m ? 'primary' : 'default'" @click="toggle('material', m)">{{ m }}</van-tag>
          </div>
        </div>
        <div class="fg"><label>信息主题</label>
          <div class="opts">
            <van-tag v-for="t in allTopics" :key="t" size="large"
              :type="filter.category === t ? 'primary' : 'default'" @click="toggle('category', t)">{{ t }}</van-tag>
          </div>
        </div>
        <div class="fg"><label>获取方式</label>
          <div class="opts">
            <van-tag v-for="c in allChannels" :key="c" size="large"
              :type="filter.channel === c ? 'primary' : 'default'" @click="toggle('channel', c)">{{ c }}</van-tag>
          </div>
        </div>
        <div class="fg"><label>提交人</label>
          <div class="opts">
            <van-tag v-for="s in meta.submitters" :key="s.id" size="large"
              :type="filter.submitter_id === s.id ? 'primary' : 'default'" @click="toggle('submitter_id', s.id)">{{ s.name }}</van-tag>
          </div>
        </div>
        <div class="fg"><label>可信度 / 状态 / 审批</label>
          <div class="opts">
            <van-tag v-for="c in meta.credibility" :key="c" size="large"
              :type="filter.credibility === c ? 'primary' : 'default'" @click="toggle('credibility', c)">可信·{{ c }}</van-tag>
            <van-tag v-for="s in meta.status" :key="s" size="large"
              :type="filter.status === s ? 'success' : 'default'" @click="toggle('status', s)">{{ s }}</van-tag>
            <van-tag v-for="a in ['待审批', '已通过', '已驳回']" :key="a" size="large"
              :type="filter.approval === a ? 'warning' : 'default'" @click="toggle('approval', a)">{{ a }}</van-tag>
          </div>
        </div>
        <div class="fg"><label>提交时间</label>
          <div class="opts time-range">
            <van-field v-model="filter.date_from" is-link readonly placeholder="开始日期" @click="showCalendar = true" />
            <van-field v-model="filter.date_to" is-link readonly placeholder="结束日期" @click="showCalendar = true" />
          </div>
        </div>
        <div class="filter-actions">
          <van-button block @click="clearFilter">重 置</van-button>
          <van-button block type="primary" @click="applyFilter">确 定</van-button>
        </div>
      </div>
    </van-popup>
    <van-calendar v-model:show="showCalendar" type="range" @confirm="onDate" :min-date="minDate" :max-date="maxDate" />
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import api from '../api'

const router = useRouter()
const route = useRoute()
const items = ref([])
const kw = ref('')
const sort = ref('fresh')
const loading = ref(false)
const refreshing = ref(false)
const showFilter = ref(false)
const showCalendar = ref(false)
const onlyFollowing = ref(false)
const meta = ref({ taxonomy: { depts: [], materials: [], topics: {}, channels: {} }, credibility: [], status: [], submitters: [] })
const filter = reactive({ dept: '', material: '', category: '', channel: '', submitter_id: '', credibility: '', status: '', approval: '', date_from: '', date_to: '' })
const minDate = new Date(2025, 0, 1)
const maxDate = new Date(2027, 11, 31)

const tax = computed(() => meta.value.taxonomy)
const allTopics = computed(() => [...new Set(Object.values(tax.value.topics || {}).flat())])
const allChannels = computed(() => [...new Set(Object.values(tax.value.channels || {}).flat())])
const hasFilter = computed(() => Object.values(filter).some(v => v !== ''))

function toggle(key, val) { filter[key] = filter[key] === val ? '' : val }
function clearFilter() {
  Object.keys(filter).forEach(k => filter[k] = '')
  showFilter.value = false
  load()
}
function applyFilter() { showFilter.value = false; load() }
function fmt(d) { return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}` }
function onDate([s, e]) { filter.date_from = fmt(s); filter.date_to = fmt(e); showCalendar.value = false }
function fmtTime(t) { return t ? t.slice(5, 16).replace('T', ' ') : '' }

async function load() {
  loading.value = true
  try {
    const params = { sort: sort.value, keyword: kw.value || undefined, following: onlyFollowing.value ? 1 : undefined }
    Object.entries(filter).forEach(([k, v]) => { if (v !== '') params[k] = v })
    if (route.query.my_tags) params.my_tags = route.query.my_tags
    const res = await api.get('/clues', { params })
    items.value = res.items
  } finally {
    loading.value = false
    refreshing.value = false
  }
}

async function toggleLike(c) {
  const res = await api.post(`/clues/${c.id}/like`)
  c.liked = res.liked; c.likes = res.likes
}

function goDetail(id) { router.push(`/clue/${id}`) }

onMounted(async () => {
  meta.value = await api.get('/meta')
  load()
})
</script>

<style scoped>
.hero { background: linear-gradient(135deg, #2b6cff 0%, #4d9dff 100%); color: #fff; padding: 18px 20px 14px; }
.hero-title { font-size: 20px; font-weight: 700; letter-spacing: 1px; display: flex; align-items: baseline; gap: 10px; }
.hero-dept { font-size: 12px; font-weight: 400; opacity: .85; }
.hero-sub { font-size: 12px; opacity: .8; margin-top: 4px; letter-spacing: 2px; }
.topbar { display: flex; align-items: center; background: #fff; }
.topbar .van-search { flex: 1; }
.filter-btn { display: flex; flex-direction: column; align-items: center; padding: 0 14px; color: #1989fa; font-size: 11px; }
.quick-filter { display: flex; align-items: center; gap: 10px; padding: 6px 16px; background: #fff; border-top: 1px solid #f2f2f2; font-size: 13px; }
.clue-card { background: #fff; margin: 10px 12px; border-radius: 14px; padding: 16px; box-shadow: 0 2px 10px rgba(43, 108, 255, .07); transition: transform .15s; }
.clue-card:active { transform: scale(.99); }
.mini-avatar { width: 18px; height: 18px; border-radius: 50%; margin-right: 4px; vertical-align: middle; }
.card-head { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
.cred { margin-left: auto; font-size: 11px; }
.cred-高 { color: #07c160; } .cred-中 { color: #ff976a; } .cred-低 { color: #969799; }
.card-title { margin: 8px 0 4px; font-size: 16px; }
.card-content { margin: 0; color: #646566; font-size: 13px; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
.card-kws { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 8px; }
.card-foot { display: flex; align-items: center; margin-top: 10px; font-size: 12px; color: #969799; }
.submitter { font-weight: 500; color: #576b95; margin-right: 8px; }
.stats { margin-left: auto; display: flex; gap: 14px; }
.stats span { display: flex; align-items: center; gap: 3px; }
.liked { color: #ee0a24; }
.filter-panel { padding: 20px 16px 30px; overflow-y: auto; }
.filter-panel h3 { margin: 0 0 12px; }
.fg { margin-bottom: 14px; }
.fg label { display: block; font-size: 13px; color: #969799; margin-bottom: 8px; }
.opts { display: flex; flex-wrap: wrap; gap: 8px; }
.time-range { display: flex; gap: 8px; }
.time-range .van-field { background: #f7f8fa; border-radius: 8px; padding: 8px 12px; }
.filter-actions { display: flex; gap: 12px; margin-top: 20px; }
</style>
