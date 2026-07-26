import SearchBox from "./search-box";
import SafeModeButton from "./safe-mode-button";
import UserMenu from "./user-menu";

/** 悬浮顶栏胶囊：高 56px，glass-bar 底 + e1 投影，左右 20px、顶部 16px 由
 *  外层 header 留白控制；sticky 悬浮在内容之上。
 *  内容从左到右：渐变圆点 logo + 品牌字、搜索胶囊（flex-1）、安全模式按钮、
 *  渐变头像用户菜单。 */
export default function Topbar() {
  return (
    <header className="sticky top-0 z-40 px-5 pb-0.5 pt-4">
      <div className="glass-bar flex h-14 items-center gap-2.5 rounded-pill pl-[18px] pr-3 shadow-e1">
        <div className="flex shrink-0 items-center gap-2.5">
          <span aria-hidden className="h-[26px] w-[26px] rounded-pill bg-grad-accent" />
          <span className="font-brand text-[15px] font-bold">PM Gallery</span>
        </div>
        <SearchBox />
        <SafeModeButton />
        <UserMenu />
      </div>
    </header>
  );
}
