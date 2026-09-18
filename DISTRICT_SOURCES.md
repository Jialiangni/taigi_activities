# 各區圖書館與活動中心來源

新增54個圖書館分區來源與54個活動中心公告來源，臺北12、新北29、桃園13區均有入口。現有158個收集器，registry149個。這是來源範圍，不是158個已核實活動，也不是每一場館完整行程。

## 收集方式

- 臺北圖書館：官方閱讀網53個分館／閱覽室活動列表，分成12區；沿同一分館數字頁碼翻頁。總館與其他特殊館別仍由原有tpml來源補充。
- 新北圖書館：官方area選項對應29區，不指定branch以包含同區各館；跟隨原站pagechange表單，以同一Cookie及CSRF續頁。代碼採2026-09-18較早成功取得的官方HTML；此次新增驗收如遇HTTP502明確列failed，並不代表該區沒有活動。
- 桃園圖書館：官方GetVenues行政區／館舍JSON，完整Filter[0]至Filter[4]查詢與CurrentPage表單翻頁；桃園區含總館，逐項檢查data-area，篩選未生效即報錯。
- 活動中心：從各區公所公告、活動、研習及中心相關公開頁發現內容；需中心及台語相關證據，不將租借辦法與收費規則當作活動。沒有獨立官網、只在社群或圖片公布的課表仍可能漏收。
- 每入口預設30頁，包含列表與詳情。圖書館列表最多約半數預算（至少容納初始各館列表），優先讀取有台語關鍵字的詳情；未讀完標partial。
- 收集階段全部候選待核實，不從來源所屬行政區推定場地。本輪14筆候選已逐筆審閱，核實刊登18個場次與4項資訊；詳見下方結果。

## 官方名錄依據

- [臺北市行政區／區公所](https://www.gov.taipei/cp.aspx?n=1F076481DD9E556B)
- [新北市民政局區公所圖像地圖](https://www.ca.ntpc.gov.tw/home.jsp?id=98)
- [桃園市官方區公所連結](https://land.tycg.gov.tw/News_Link.aspx?n=4143&sms=10099)
- [臺北圖書館依單位查詢](https://reading.tpml.gov.taipei/Content_List.aspx?n=99FE082EB4C0BDA5)
- [新北圖書館行政區篩選](https://www.library.ntpc.gov.tw/multiplehtml/ActvInfo)
- [桃園圖書館公開行政區與館舍資料](https://www.typl.gov.tw/zh-tw/Home/GetVenues)

## 最新逐入口驗收

已完成108個新增入口的連線驗收：69個partial、30個failed、9個ok；取得14筆候選，後續核實結果如下。

30個failed包含新北圖書館29區HTTP502（首頁及館別介面交叉檢查亦502），以及桃園區公所一個影音頁逾時。八里區公所的深層HTML及帶參數PDF下載問題已修正，30頁重測無錯誤。其餘69個partial皆為本次頁數預算限制。108個入口普遍採10頁驗收，八里、桃園區公所、松山區圖書館、桃園區圖書館、復興區圖書館另採30頁重測。日常預設為每入口30頁。

完整時間、請求數、入口回應指紋及候選索引見 [驗收報告](data/audit/2026-09-18-district-collection-report.json)。partial常表示本輪10或30頁上限；failed表示連線或解析失敗，不能當作無活動。

## 候選核實及刊登

- 新增18個場次：永春臺灣語初級研習班16次（2026/9/23至2027/1/6週三14:00–16:00，共32小時，須整期報名，影印費自付）；桃園10/3總館恐龍繪本及9/20會稽摺紙故事各1場，皆免費。
- 新增4項資訊：西園臺語詞卡互動、萬華台語書展、柳鄉每週一詞閱讀、舊莊臺語書展。不捏造每日場次，日期到期即移出資訊區。
- 台語親子系列3場早已刊登，不重複加入；信義舊公告已過期，板橋轉貼的活動在彰化，內湖地名沿革及萬里交通短片不屬目標活動。
- 瑞芳9/19《消失的神樹》經青雲殿主辦公告補齊18:20正式演出時間，但未取得該場明載台語演出的證據，保留待核實；其餘瓶燈活動不能一併推定台語。
- 桃園雲端亮點系列已過的單元提及台語老歌；剩餘9/24與10/1直播無台語內容證據，未刊登。

公開清單更新為81個場次及9項資訊；[逐筆紀錄](data/audit/2026-09-18-district-publication-review.json)保存14筆的來源指紋與判斷。新北圖書館HTTP502等收集限制仍存在，不能因此宣稱全部場館與近三週資訊已收齊。

## 54區入口對照

| 城市 | 行政區 | 圖書館來源 | 活動中心公告來源 |
|---|---|---|---|
| 臺北市 | 松山區 | [tpml_district_a](https://reading.tpml.gov.taipei/News.aspx?n=0CDA599F03495502&sms=9D72E82EC16F3E64)（ok） | [tp_center_ssdo](https://ssdo.gov.taipei/)（partial） |
| 臺北市 | 信義區 | [tpml_district_b](https://reading.tpml.gov.taipei/News.aspx?n=AF0E43EB498C9E89&sms=9D72E82EC16F3E64)（partial） | [tp_center_xydo](https://xydo.gov.taipei/)（partial） |
| 臺北市 | 大安區 | [tpml_district_c](https://reading.tpml.gov.taipei/News.aspx?n=8A26D7A84A1698A8&sms=9D72E82EC16F3E64)（ok） | [tp_center_dado](https://dado.gov.taipei/)（partial） |
| 臺北市 | 中山區 | [tpml_district_d](https://reading.tpml.gov.taipei/News.aspx?n=C191E73568BAB51E&sms=9D72E82EC16F3E64)（ok） | [tp_center_zsdo](https://zsdo.gov.taipei/)（partial） |
| 臺北市 | 中正區 | [tpml_district_e](https://reading.tpml.gov.taipei/News.aspx?n=3DFF12E5683E55F4&sms=9D72E82EC16F3E64)（partial） | [tp_center_zzdo](https://zzdo.gov.taipei/)（partial） |
| 臺北市 | 大同區 | [tpml_district_f](https://reading.tpml.gov.taipei/News.aspx?n=08A9B80C1E219522&sms=9D72E82EC16F3E64)（partial） | [tp_center_dtdo](https://dtdo.gov.taipei/)（partial） |
| 臺北市 | 萬華區 | [tpml_district_g](https://reading.tpml.gov.taipei/News.aspx?n=5631EFDABC442986&sms=9D72E82EC16F3E64)（partial） | [tp_center_whdo](https://whdo.gov.taipei/)（partial） |
| 臺北市 | 文山區 | [tpml_district_h](https://reading.tpml.gov.taipei/News.aspx?n=4355269DAFEEF2F8&sms=9D72E82EC16F3E64)（partial） | [tp_center_wsdo](https://wsdo.gov.taipei/)（partial） |
| 臺北市 | 南港區 | [tpml_district_i](https://reading.tpml.gov.taipei/News.aspx?n=0CD52449194E7CAA&sms=9D72E82EC16F3E64)（ok） | [tp_center_ngdo](https://ngdo.gov.taipei/)（partial） |
| 臺北市 | 內湖區 | [tpml_district_j](https://reading.tpml.gov.taipei/News.aspx?n=3703DABE8D817F11&sms=9D72E82EC16F3E64)（partial） | [tp_center_nhdo](https://nhdo.gov.taipei/)（partial） |
| 臺北市 | 士林區 | [tpml_district_k](https://reading.tpml.gov.taipei/News.aspx?n=B892A2F0FA7E99E5&sms=9D72E82EC16F3E64)（partial） | [tp_center_sldo](https://sldo.gov.taipei/)（partial） |
| 臺北市 | 北投區 | [tpml_district_l](https://reading.tpml.gov.taipei/News.aspx?n=DAD93C3C71996A94&sms=9D72E82EC16F3E64)（partial） | [tp_center_btdo](https://btdo.gov.taipei/)（partial） |
| 新北市 | 八里區 | [ntpclib_district_249](https://www.library.ntpc.gov.tw/multiplehtml/ActvInfo?area=249)（failed） | [ntpc_center_bali](https://www.bali.ntpc.gov.tw/)（partial） |
| 新北市 | 三芝區 | [ntpclib_district_252](https://www.library.ntpc.gov.tw/multiplehtml/ActvInfo?area=252)（failed） | [ntpc_center_sanzhi](https://www.sanzhi.ntpc.gov.tw/)（partial） |
| 新北市 | 三重區 | [ntpclib_district_241](https://www.library.ntpc.gov.tw/multiplehtml/ActvInfo?area=241)（failed） | [ntpc_center_sanchong](https://www.sanchong.ntpc.gov.tw/)（partial） |
| 新北市 | 三峽區 | [ntpclib_district_237](https://www.library.ntpc.gov.tw/multiplehtml/ActvInfo?area=237)（failed） | [ntpc_center_sanxia](https://www.sanxia.ntpc.gov.tw/)（partial） |
| 新北市 | 土城區 | [ntpclib_district_236](https://www.library.ntpc.gov.tw/multiplehtml/ActvInfo?area=236)（failed） | [ntpc_center_tucheng](https://www.tucheng.ntpc.gov.tw/)（partial） |
| 新北市 | 中和區 | [ntpclib_district_235](https://www.library.ntpc.gov.tw/multiplehtml/ActvInfo?area=235)（failed） | [ntpc_center_zhonghe](https://www.zhonghe.ntpc.gov.tw/)（partial） |
| 新北市 | 五股區 | [ntpclib_district_248](https://www.library.ntpc.gov.tw/multiplehtml/ActvInfo?area=248)（failed） | [ntpc_center_wugu](https://www.wugu.ntpc.gov.tw/)（partial） |
| 新北市 | 平溪區 | [ntpclib_district_226](https://www.library.ntpc.gov.tw/multiplehtml/ActvInfo?area=226)（failed） | [ntpc_center_pingxi](https://www.pingxi.ntpc.gov.tw/)（partial） |
| 新北市 | 永和區 | [ntpclib_district_234](https://www.library.ntpc.gov.tw/multiplehtml/ActvInfo?area=234)（failed） | [ntpc_center_yonghe](https://www.yonghe.ntpc.gov.tw/)（partial） |
| 新北市 | 石門區 | [ntpclib_district_253](https://www.library.ntpc.gov.tw/multiplehtml/ActvInfo?area=253)（failed） | [ntpc_center_shimen](https://www.shimen.ntpc.gov.tw/)（partial） |
| 新北市 | 石碇區 | [ntpclib_district_223](https://www.library.ntpc.gov.tw/multiplehtml/ActvInfo?area=223)（failed） | [ntpc_center_shiding](https://www.shiding.ntpc.gov.tw/)（partial） |
| 新北市 | 汐止區 | [ntpclib_district_221](https://www.library.ntpc.gov.tw/multiplehtml/ActvInfo?area=221)（failed） | [ntpc_center_xizhi](https://www.xizhi.ntpc.gov.tw/)（partial） |
| 新北市 | 坪林區 | [ntpclib_district_232](https://www.library.ntpc.gov.tw/multiplehtml/ActvInfo?area=232)（failed） | [ntpc_center_pinglin](https://www.pinglin.ntpc.gov.tw/)（partial） |
| 新北市 | 林口區 | [ntpclib_district_244](https://www.library.ntpc.gov.tw/multiplehtml/ActvInfo?area=244)（failed） | [ntpc_center_linkou](https://www.linkou.ntpc.gov.tw/)（partial） |
| 新北市 | 板橋區 | [ntpclib_district_220](https://www.library.ntpc.gov.tw/multiplehtml/ActvInfo?area=220)（failed） | [ntpc_center_banqiao](https://www.banqiao.ntpc.gov.tw/)（partial） |
| 新北市 | 金山區 | [ntpclib_district_208](https://www.library.ntpc.gov.tw/multiplehtml/ActvInfo?area=208)（failed） | [ntpc_center_jinshan](https://www.jinshan.ntpc.gov.tw/)（partial） |
| 新北市 | 泰山區 | [ntpclib_district_243](https://www.library.ntpc.gov.tw/multiplehtml/ActvInfo?area=243)（failed） | [ntpc_center_taishan](https://www.taishan.ntpc.gov.tw/)（partial） |
| 新北市 | 烏來區 | [ntpclib_district_233](https://www.library.ntpc.gov.tw/multiplehtml/ActvInfo?area=233)（failed） | [ntpc_center_wulai](https://www.wulai.ntpc.gov.tw/)（partial） |
| 新北市 | 貢寮區 | [ntpclib_district_228](https://www.library.ntpc.gov.tw/multiplehtml/ActvInfo?area=228)（failed） | [ntpc_center_gongliao](https://www.gongliao.ntpc.gov.tw/)（partial） |
| 新北市 | 淡水區 | [ntpclib_district_251](https://www.library.ntpc.gov.tw/multiplehtml/ActvInfo?area=251)（failed） | [ntpc_center_tamsui](https://www.tamsui.ntpc.gov.tw/)（partial） |
| 新北市 | 深坑區 | [ntpclib_district_222](https://www.library.ntpc.gov.tw/multiplehtml/ActvInfo?area=222)（failed） | [ntpc_center_shenkeng](https://www.shenkeng.ntpc.gov.tw/)（partial） |
| 新北市 | 新店區 | [ntpclib_district_231](https://www.library.ntpc.gov.tw/multiplehtml/ActvInfo?area=231)（failed） | [ntpc_center_xindian](https://www.xindian.ntpc.gov.tw/)（partial） |
| 新北市 | 新莊區 | [ntpclib_district_242](https://www.library.ntpc.gov.tw/multiplehtml/ActvInfo?area=242)（failed） | [ntpc_center_xinzhuang](https://www.xinzhuang.ntpc.gov.tw/)（partial） |
| 新北市 | 瑞芳區 | [ntpclib_district_224](https://www.library.ntpc.gov.tw/multiplehtml/ActvInfo?area=224)（failed） | [ntpc_center_ruifang](https://www.ruifang.ntpc.gov.tw/)（partial） |
| 新北市 | 萬里區 | [ntpclib_district_207](https://www.library.ntpc.gov.tw/multiplehtml/ActvInfo?area=207)（failed） | [ntpc_center_wanli](https://www.wanli.ntpc.gov.tw/)（partial） |
| 新北市 | 樹林區 | [ntpclib_district_238](https://www.library.ntpc.gov.tw/multiplehtml/ActvInfo?area=238)（failed） | [ntpc_center_shulin](https://www.shulin.ntpc.gov.tw/)（partial） |
| 新北市 | 雙溪區 | [ntpclib_district_227](https://www.library.ntpc.gov.tw/multiplehtml/ActvInfo?area=227)（failed） | [ntpc_center_shuangxi](https://www.shuangxi.ntpc.gov.tw/)（partial） |
| 新北市 | 蘆洲區 | [ntpclib_district_247](https://www.library.ntpc.gov.tw/multiplehtml/ActvInfo?area=247)（failed） | [ntpc_center_luzhou](https://www.luzhou.ntpc.gov.tw/)（partial） |
| 新北市 | 鶯歌區 | [ntpclib_district_239](https://www.library.ntpc.gov.tw/multiplehtml/ActvInfo?area=239)（failed） | [ntpc_center_yingge](https://www.yingge.ntpc.gov.tw/)（partial） |
| 桃園市 | 桃園區 | [typl_district_2](https://www.typl.gov.tw/zh-tw/Activity?Filter%5B0%5D=&Filter%5B1%5D=&Filter%5B2%5D=&Filter%5B3%5D=&Filter%5B4%5D=2.1&keyword=)（partial） | [ty_center_tao](https://www.tao.tycg.gov.tw/)（failed） |
| 桃園市 | 中壢區 | [typl_district_3](https://www.typl.gov.tw/zh-tw/Activity?Filter%5B0%5D=&Filter%5B1%5D=&Filter%5B2%5D=&Filter%5B3%5D=&Filter%5B4%5D=3&keyword=)（partial） | [ty_center_zhongli](https://www.zhongli.tycg.gov.tw/)（partial） |
| 桃園市 | 蘆竹區 | [typl_district_4](https://www.typl.gov.tw/zh-tw/Activity?Filter%5B0%5D=&Filter%5B1%5D=&Filter%5B2%5D=&Filter%5B3%5D=&Filter%5B4%5D=4&keyword=)（ok） | [ty_center_luzhu](https://www.luzhu.tycg.gov.tw/)（partial） |
| 桃園市 | 龍潭區 | [typl_district_5](https://www.typl.gov.tw/zh-tw/Activity?Filter%5B0%5D=&Filter%5B1%5D=&Filter%5B2%5D=&Filter%5B3%5D=&Filter%5B4%5D=5&keyword=)（ok） | [ty_center_longtan](https://www.longtan.tycg.gov.tw/)（partial） |
| 桃園市 | 龜山區 | [typl_district_6](https://www.typl.gov.tw/zh-tw/Activity?Filter%5B0%5D=&Filter%5B1%5D=&Filter%5B2%5D=&Filter%5B3%5D=&Filter%5B4%5D=6&keyword=)（partial） | [ty_center_guishan](https://www.guishan.tycg.gov.tw/)（partial） |
| 桃園市 | 平鎮區 | [typl_district_7](https://www.typl.gov.tw/zh-tw/Activity?Filter%5B0%5D=&Filter%5B1%5D=&Filter%5B2%5D=&Filter%5B3%5D=&Filter%5B4%5D=7&keyword=)（partial） | [ty_center_pingzhen](https://www.pingzhen.tycg.gov.tw/)（partial） |
| 桃園市 | 八德區 | [typl_district_8](https://www.typl.gov.tw/zh-tw/Activity?Filter%5B0%5D=&Filter%5B1%5D=&Filter%5B2%5D=&Filter%5B3%5D=&Filter%5B4%5D=8&keyword=)（partial） | [ty_center_bade](https://www.bade.tycg.gov.tw/)（partial） |
| 桃園市 | 楊梅區 | [typl_district_9](https://www.typl.gov.tw/zh-tw/Activity?Filter%5B0%5D=&Filter%5B1%5D=&Filter%5B2%5D=&Filter%5B3%5D=&Filter%5B4%5D=9&keyword=)（partial） | [ty_center_yangmei](https://www.yangmei.tycg.gov.tw/)（partial） |
| 桃園市 | 大園區 | [typl_district_10](https://www.typl.gov.tw/zh-tw/Activity?Filter%5B0%5D=&Filter%5B1%5D=&Filter%5B2%5D=&Filter%5B3%5D=&Filter%5B4%5D=10&keyword=)（ok） | [ty_center_dayuan](https://www.dayuan.tycg.gov.tw/)（partial） |
| 桃園市 | 觀音區 | [typl_district_11](https://www.typl.gov.tw/zh-tw/Activity?Filter%5B0%5D=&Filter%5B1%5D=&Filter%5B2%5D=&Filter%5B3%5D=&Filter%5B4%5D=11&keyword=)（partial） | [ty_center_guanyin](https://www.guanyin.tycg.gov.tw/)（partial） |
| 桃園市 | 大溪區 | [typl_district_12](https://www.typl.gov.tw/zh-tw/Activity?Filter%5B0%5D=&Filter%5B1%5D=&Filter%5B2%5D=&Filter%5B3%5D=&Filter%5B4%5D=12&keyword=)（partial） | [ty_center_daxi](https://www.daxi.tycg.gov.tw/)（partial） |
| 桃園市 | 新屋區 | [typl_district_13](https://www.typl.gov.tw/zh-tw/Activity?Filter%5B0%5D=&Filter%5B1%5D=&Filter%5B2%5D=&Filter%5B3%5D=&Filter%5B4%5D=13&keyword=)（ok） | [ty_center_xinwu](https://www.xinwu.tycg.gov.tw/)（partial） |
| 桃園市 | 復興區 | [typl_district_14](https://www.typl.gov.tw/zh-tw/Activity?Filter%5B0%5D=&Filter%5B1%5D=&Filter%5B2%5D=&Filter%5B3%5D=&Filter%5B4%5D=14&keyword=)（ok） | [ty_center_fuxing](https://www.fuxing.tycg.gov.tw/)（partial） |
