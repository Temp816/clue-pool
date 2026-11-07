<template>
  <div class="welcome">
    <!-- Hero -->
    <div class="hero">
      <img src="/icons/icon-512.png" class="logo" alt="线索池" />
      <h1>线索池</h1>
      <p class="dept">原价中心 · SCC · 情报协作平台</p>
      <p class="slogan">让每一条线索，都成为部门共有的情报资产</p>
      <div class="hero-badges">
        <span>广泛收集</span><span>按需取用</span><span>持续深挖</span>
      </div>
    </div>

    <!-- 二维码 -->
    <div class="card qr-card">
      <h2>📱 扫码立即体验</h2>
      <canvas ref="qrCanvas" class="qr"></canvas>
      <p class="url">{{ appUrl }}</p>
      <p class="qr-tip">iPhone / 安卓 / 电脑 浏览器打开即用，无需下载</p>
    </div>

    <!-- 核心亮点 -->
    <div class="card">
      <h2>✨ 为什么值得选择</h2>
      <div class="features">
        <div class="feat"><i>⚡</i><div><b>30 秒极速录入</b><p>语音转文字、拍照识别、先记后补，跑现场也能随手提交</p></div></div>
        <div class="feat"><i>🔍</i><div><b>多维检索</b><p>最新/热门/阅读/点赞排序，条线·物料·主题·时间组合筛选</p></div></div>
        <div class="feat"><i>🤖</i><div><b>智能推荐 · 数据不出本机</b><p>默认本地引擎推荐分类标签，情报内容零外传</p></div></div>
        <div class="feat"><i>🛡️</i><div><b>四类权限隔离</b><p>结构件/电子料/化工料/CI 分权可见，谁也看不到越权信息</p></div></div>
        <div class="feat"><i>✅</i><div><b>范围审批流</b><p>审批员按负责范围把关，通过/驳回/意见全程留痕</p></div></div>
        <div class="feat"><i>📊</i><div><b>管理驾驶舱</b><p>趋势、分布、活跃榜一目了然，一键导出完整 Excel</p></div></div>
      </div>
    </div>

    <!-- 安装到桌面 -->
    <div class="card">
      <h2>📲 安装到桌面（四端通用）</h2>
      <div class="install-list">
        <div class="inst">
          <span class="platform ios">iPhone / iPad</span>
          <p>Safari 打开链接 → 底部「分享」→「添加到主屏幕」</p>
        </div>
        <div class="inst">
          <span class="platform android">安卓 Android</span>
          <p>Chrome 打开链接 → 右上角菜单 →「安装应用 / 添加到主屏幕」</p>
        </div>
        <div class="inst">
          <span class="platform win">Windows</span>
          <p>Chrome / Edge 打开链接 → 地址栏右侧「安装」图标</p>
        </div>
        <div class="inst">
          <span class="platform mac">Mac</span>
          <p>Chrome 打开链接 → 地址栏右侧「安装」图标</p>
        </div>
      </div>
      <p class="inst-tip">安装后桌面生成独立图标，点开即全屏 App 体验</p>
    </div>

    <!-- 演示账号 -->
    <div class="card">
      <h2>👥 演示账号一览</h2>
      <div class="accounts">
        <div class="acct">
          <div class="acct-head"><b>管理员</b><span class="role admin">管理员</span></div>
          <p><code>admin</code> / <code>admin123</code></p>
          <p class="desc">全部权限 · 账号分配 · 批量导入 · 标签体系 · 数据看板 · 导出</p>
        </div>
        <div class="acct">
          <div class="acct-head"><b>演示用户</b><span class="role submit">提交人</span><span class="role view">查看人</span></div>
          <p><code>demo</code> / <code>demo123</code></p>
          <p class="desc">权限：结构件/电子料/CI（无化工料权限，可现场对比权限隔离效果）</p>
        </div>
        <div class="acct">
          <div class="acct-head"><b>审批员</b><span class="role approve">审批员</span></div>
          <p><code>reviewer</code> / <code>review123</code></p>
          <p class="desc">负责范围：结构件 —— 打开结构件线索详情即可体验审批操作</p>
        </div>
      </div>
    </div>

    <div class="footer">
      <p>线索池 Beta · 原价中心 SCC</p>
      <p class="slogan2">让每条线索都有价值</p>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import QRCode from 'qrcode'

const qrCanvas = ref(null)
const appUrl = location.origin

onMounted(() => {
  QRCode.toCanvas(qrCanvas.value, appUrl, {
    width: 220, margin: 1,
    color: { dark: '#2b6cff', light: '#ffffff' },
  })
})
</script>

<style scoped>
.welcome { min-height: 100vh; background: #f4f6fa; padding-bottom: 30px; }
.hero { background: linear-gradient(160deg, #1e56e8 0%, #2b6cff 45%, #5aa5ff 100%); color: #fff; text-align: center; padding: 48px 24px 40px; border-radius: 0 0 32px 32px; }
.logo { width: 88px; height: 88px; border-radius: 22px; box-shadow: 0 8px 24px rgba(0,0,0,.25); }
.hero h1 { font-size: 34px; letter-spacing: 6px; margin: 14px 0 4px; }
.dept { font-size: 14px; letter-spacing: 2px; opacity: .92; margin: 0 0 10px; }
.slogan { font-size: 15px; opacity: .9; margin: 0 0 16px; }
.hero-badges { display: flex; justify-content: center; gap: 10px; }
.hero-badges span { border: 1px solid rgba(255,255,255,.5); border-radius: 20px; padding: 4px 14px; font-size: 12px; }
.card { background: #fff; margin: 16px 14px 0; border-radius: 18px; padding: 22px 20px; box-shadow: 0 4px 20px rgba(43,108,255,.08); }
.card h2 { font-size: 17px; margin: 0 0 14px; }
.qr-card { text-align: center; }
.qr { width: 220px; height: 220px; border-radius: 12px; }
.url { color: #2b6cff; font-size: 13px; word-break: break-all; background: #eef4ff; border-radius: 8px; padding: 8px 12px; margin: 12px 0 6px; }
.qr-tip { color: #969799; font-size: 12px; margin: 0; }
.features { display: flex; flex-direction: column; gap: 14px; }
.feat { display: flex; gap: 12px; align-items: flex-start; }
.feat i { font-style: normal; font-size: 24px; width: 40px; height: 40px; background: #eef4ff; border-radius: 12px; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.feat b { font-size: 14px; }
.feat p { margin: 3px 0 0; font-size: 12px; color: #646566; line-height: 1.5; }
.install-list { display: flex; flex-direction: column; gap: 10px; }
.inst { background: #f7f9ff; border-radius: 12px; padding: 12px 14px; }
.inst p { margin: 6px 0 0; font-size: 12px; color: #646566; }
.platform { font-size: 12px; font-weight: 600; color: #fff; border-radius: 6px; padding: 3px 10px; }
.platform.ios { background: #333; } .platform.android { background: #07c160; }
.platform.win { background: #2b6cff; } .platform.mac { background: #576b95; }
.inst-tip { text-align: center; color: #969799; font-size: 12px; margin: 12px 0 0; }
.accounts { display: flex; flex-direction: column; gap: 12px; }
.acct { border: 1px solid #eef0f5; border-radius: 12px; padding: 12px 14px; }
.acct-head { display: flex; align-items: center; gap: 6px; margin-bottom: 6px; }
.acct code { background: #eef4ff; color: #2b6cff; border-radius: 6px; padding: 2px 8px; font-size: 13px; }
.acct p { margin: 4px 0; font-size: 13px; }
.acct .desc { color: #969799; font-size: 11px; }
.role { font-size: 10px; border-radius: 4px; padding: 2px 6px; color: #fff; }
.role.admin { background: #2b6cff; } .role.submit { background: #07c160; }
.role.view { background: #909399; } .role.approve { background: #ff976a; }
.footer { text-align: center; color: #b0b6c3; padding: 24px 0 8px; font-size: 12px; }
.footer .slogan2 { letter-spacing: 3px; }
</style>
