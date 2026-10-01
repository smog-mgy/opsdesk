-- =============================================================
-- ch11 · 工程师工单处理闭环
-- tickets 表扩展:状态枚举升级(带流转)、优先级、处理人、处理备注、更新时间
-- 安全顺序:先扩枚举(保留旧值)→ 归一旧值 → 收缩枚举 → 加工程侧字段
-- 执行:docker exec -i opsdesk-mysql mysql --default-character-set=utf8mb4 -uroot -proot opsdesk < sql/ch11-engineer-ticket.sql
-- =============================================================

-- 确保中文 ENUM 定义值按 utf8mb4 解析
SET NAMES utf8mb4;

-- ① 先扩展枚举(保留旧值),让旧行可被 UPDATE 归一
ALTER TABLE tickets
  MODIFY COLUMN status ENUM('待处理','已处理','待派单','处理中','待配件','已解决')
    NOT NULL DEFAULT '待派单' COMMENT '处理状态(过渡)';

-- ② 旧值归一:待处理→待派单,已处理→已解决
UPDATE tickets
  SET status = CASE status WHEN '待处理' THEN '待派单' WHEN '已处理' THEN '已解决' ELSE status END;

-- ③ 收缩为工程侧四态
ALTER TABLE tickets
  MODIFY COLUMN status ENUM('待派单','处理中','待配件','已解决')
    NOT NULL DEFAULT '待派单' COMMENT '处理状态:待派单→处理中→待配件→已解决';

-- ④ 加工程侧字段:优先级 / 处理人 / 处理备注 / 更新时间
ALTER TABLE tickets
  ADD COLUMN priority      ENUM('P1','P2','P3')  NOT NULL DEFAULT 'P2'   COMMENT '优先级' AFTER status,
  ADD COLUMN handler       VARCHAR(32)           NULL                     COMMENT '处理人' AFTER priority,
  ADD COLUMN progress_note VARCHAR(512)          NULL                     COMMENT '处理备注/进度' AFTER handler,
  ADD COLUMN updated_at    DATETIME              NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间' AFTER created_at;
