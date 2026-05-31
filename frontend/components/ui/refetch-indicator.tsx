"use client";

/**
 * 后台刷新指示：顶部一条极淡的滑动光带。
 * 仅在 react-query「有旧数据但正在后台 refetch」时显示，
 * 不退回骨架、不打断阅读。
 */
export function RefetchIndicator({ active }: { active: boolean }) {
  if (!active) return null;
  return <div className="refetch-bar" role="status" aria-label="刷新中" />;
}
