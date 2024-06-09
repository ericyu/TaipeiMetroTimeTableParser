# 台北捷運時刻表轉換程式

轉換後的時刻表直接放在 https://github.com/ericyu/TaipeiMetroTimeTable 供取用。

注意：
- 新北投支線及小碧潭支線目前會跳過。文湖線則是沒有公佈時刻表。
- 請先至 https://tdx.transportdata.tw/api-service/swagger/basic/268fc230-2e04-471b-a728-a726167c1cfc#/Metro/MetroApi_StationTimeTable_2104 取得資料，再以 `ParseTimeTables.py` 轉成自有格式（前一版自行解析 PDF 時使用的 JSON 格式）。

## 解析時刻表
ParseTimeTables.py 從 fetchData 目錄讀進 PDF 並輸出到 output 目錄下。分為 Compact / Readable 兩種，可依需求取用。

轉換後的時刻表直接放在 https://github.com/ericyu/TaipeiMetroTimeTable 供取用。
