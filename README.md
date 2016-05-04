# 台北捷運時刻表轉換程式

捷運時刻表採用 PDF，將其轉換為 JSON 格式。特點是處理了底線，所以輸出結果中包含了該班車終點站的資訊。

轉換後的時刻表直接放在 https://github.com/ericyu/TaipeiMetroTimeTable 供取用。

主要程式有兩個，以下說明。

注意：
- 採用目前還沒採用的新式車站編號，日後仍有變動的可能性。
- 新北投支線及小碧潭支線由於格式不同，目前會跳過。文湖線則是沒有公佈時刻表。
- 解析時刻表的程式採用 pdfminer 解析 PDF，執行會蠻花時間的（預設用 4 threads 執行，可在程式碼開頭修改）。

## 抓取時刻表
FetchTimeTables.py 會從台北捷運公司網站抓下所有的時刻表 PDF 檔案。輸入的是 StationList.json，裡面預先放置了各站對應的時刻表頁面 ID。結果會存放到 fetchData 目錄下。

預設不抓取 PDF，須在程式開頭修改。

## 解析時刻表
ParseTimeTables.py 從 fetchData 目錄讀進 PDF 並輸出到 output 目錄下。分為 Compact / Readable 兩種，可依需求取用。

轉換後的時刻表直接放在 https://github.com/ericyu/TaipeiMetroTimeTable 供取用。
