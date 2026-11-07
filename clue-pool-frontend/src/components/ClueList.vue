<template>
  <div class="clue-list">
    <div v-for="c in items" :key="c.id" class="clue-card" @click="$router.push(`/clue/${c.id}`)">
      <div class="head">
        <van-tag type="primary" plain>{{ c.category }}</van-tag>
        <van-tag :type="{ '待补充': 'warning', '待核实': 'primary', '已核实': 'success', '已归档': 'default' }[c.status]">
          {{ c.status }}
        </van-tag>
      </div>
      <h4>{{ c.title }}</h4>
      <div class="foot">
        <span>{{ c.submitter_name }} · {{ c.created_at?.slice(0, 10) }}</span>
        <span class="stats"><van-icon name="eye-o" /> {{ c.views }}　<van-icon name="good-job-o" /> {{ c.likes }}</span>
      </div>
    </div>
    <van-empty v-if="!items.length" description="暂无数据" />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import api from '../api'

const props = defineProps({ params: Object })
const items = ref([])

async function reload() {
  const res = await api.get('/clues', { params: props.params })
  items.value = res.items
}
defineExpose({ reload })
onMounted(reload)
</script>

<style scoped>
.clue-card { background: #fff; margin: 10px 12px; border-radius: 12px; padding: 14px; }
.head { display: flex; gap: 6px; }
h4 { margin: 8px 0; }
.foot { display: flex; font-size: 12px; color: #969799; }
.stats { margin-left: auto; }
</style>
