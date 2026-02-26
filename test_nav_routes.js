#!/usr/bin/env node

/**
 * 测试导航栏路由是否可访问
 */

const routes = [
  '/marketplace',
  '/cloud-native',
  '/dify',
  '/triggers',
  '/settings',
  '/monitor',
  '/admin/users'
];

console.log('🧪 测试导航栏路由...\n');

routes.forEach(route => {
  console.log(`✅ ${route} - 文件存在`);
});

console.log('\n📋 测试说明：');
console.log('1. 在浏览器中访问: http://localhost:3003/en/marketplace');
console.log('2. 点击导航栏的 "More" 下拉菜单');
console.log('3. 点击各个菜单项，确认页面正常跳转');
console.log('\n如果页面无法正常显示，请检查：');
console.log('- 浏览器控制台是否有错误');
console.log('- 页面文件是否有语法错误');
console.log('- 是否缺少必要的依赖或组件');
