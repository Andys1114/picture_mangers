import SearchBox from "./search-box";
import SafeModeButton from "./safe-mode-button";
import UserMenu from "./user-menu";

/** 悬浮顶栏胶囊：桌面（md+）56px——渐变圆点 logo + 品牌字、搜索胶囊（flex-1）、
 *  安全模式按钮、渐变头像；sticky 悬浮在内容之上，左右 20px、顶部 16px 由
 *  外层 header 留白控制。
 *  移动（<768，final-mobile 首屏）：46px 搜索胶囊行——24px logo 圆点 + 搜索
 *  占位 + 34px 头像同一行；品牌字与安全模式按钮撤下（安全开关挪进 chips 行）。 */
export default function Topbar() {
  return (
    <header className="sticky top-0 z-40 px-3 pb-0.5 pt-3 md:px-5 md:pt-4">
      <div className="glass-bar flex h-[46px] items-center gap-2 rounded-pill pl-3 pr-1.5 shadow-e1 md:h-14 md:gap-2.5 md:pl-[18px] md:pr-3">
        <div className="flex shrink-0 items-center gap-2.5">
          <span aria-hidden className="h-6 w-6 rounded-pill bg-grad-accent md:h-[26px] md:w-[26px]" />
          <span className="hidden font-brand text-[15px] font-bold md:inline">
            PM Gallery
          </span>
        </div>
        <SearchBox />
        <SafeModeButton />
        <UserMenu />
      </div>
    </header>
  );
}
