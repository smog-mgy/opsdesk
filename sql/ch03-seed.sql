-- =============================================================
-- ch03 · 合成历史服务对话(喂挖知识 job)。三段式 + SET NAMES utf8mb4 + 幂等。
-- =============================================================
SET NAMES utf8mb4;

-- 段1 查询:执行前 seed 会话数
SELECT COUNT(*) AS before_conv FROM conversations WHERE user_id LIKE 'seed-%';

-- 段2 写入:先幂等清理 seed-% 会话及其消息,再插入
DELETE FROM messages WHERE conversation_id IN (SELECT id FROM conversations WHERE user_id LIKE 'seed-%');
DELETE FROM conversations WHERE user_id LIKE 'seed-%';

INSERT INTO conversations (user_id, status) VALUES ('seed-u1', '已结束'), ('seed-u2', '已结束'), ('seed-u3', '已结束');
SET @c1 = (SELECT id FROM conversations WHERE user_id = 'seed-u1' ORDER BY id DESC LIMIT 1);
SET @c2 = (SELECT id FROM conversations WHERE user_id = 'seed-u2' ORDER BY id DESC LIMIT 1);
SET @c3 = (SELECT id FROM conversations WHERE user_id = 'seed-u3' ORDER BY id DESC LIMIT 1);

INSERT INTO messages (conversation_id, role, content) VALUES
  (@c1, 'user',      '我们这电机嗡嗡响还发烫,是不是要坏了'),
  (@c1, 'assistant', '请先提供设备编号与所在产线,我帮你登记报修。同时建议先停机检查负载与散热情况。'),
  (@c1, 'user',      '编号是 M-1001,在 3 号包装线'),
  (@c1, 'assistant', '已按 P2 优先级登记报修,值班工程师 2 小时内联系您,请保持电话畅通。'),
  (@c2, 'user',      '变频器老报过流,复位后过一会又报'),
  (@c2, 'assistant', '启动即过流多为负载卡死或电机绝缘问题,运行中过流多为负载突变或参数不当,建议先停机检查电机接线与绝缘。'),
  (@c2, 'user',      '好的,那要不要直接报修'),
  (@c2, 'assistant', '建议报修,工程师会带万用表现场测绝缘与运行参数,确认后给出处理方案。'),
  (@c3, 'user',      '晚上设备坏了找谁'),
  (@c3, 'assistant', '厂区运维 7×24 三班倒值班,夜班有当班工程师值守,紧急故障可拨打运维热线 8000。');

-- 段3 验证:seed 会话应为 3,消息应为 10
SELECT COUNT(*) AS after_conv FROM conversations WHERE user_id LIKE 'seed-%';
SELECT COUNT(*) AS after_msg FROM messages WHERE conversation_id IN (SELECT id FROM conversations WHERE user_id LIKE 'seed-%');