"use client";

import { UpdateDialog } from "@/components/layout/update-dialog";
import { useUpdaterBridge } from "@/lib/hooks/use-updater";

/**
 * 桌面端自动更新挂载点：订阅主进程事件 + 渲染自定义更新弹窗。
 * 非桌面环境下 useUpdaterBridge 不做任何事，UpdateDialog 也不渲染。
 */
export function UpdaterProvider() {
  useUpdaterBridge();
  return <UpdateDialog />;
}
