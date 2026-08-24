# バクラク事業部技術 実験報告書 — 最終構成

**文書形式:** Microsoft Word（既存の3ページを表紙・目次・課題概要として継承）  
**本文言語:** 日本語  
**本文・図版フォント:** Hiragino Maru Gothic ProN  
**構成確定日:** 2026年8月24日

## 1. 構成を決めるための原則

1. 課題文の要求へ、章単位で直接回答する。
2. 「方法」と「結果」を混ぜず、仮説・実験条件・結果・考察を追跡できるようにする。
3. 本文は設計判断と主要結果に集中し、全コーパス詳細、コード監査、stale file一覧は付録へ移す。
4. 最終採用runの27行そのものを本文へ掲載し、27/27という要約だけで終わらせない。
5. ソースコードは全文ではなく、「この仮説をどの実装が支えるか」が分かる三つの抜粋を掲載する。
6. 図は本文で先に説明し、その直後に配置する。図キャプションは下、表題は上とする。
7. 100%は、PDF、モデル、推論設定、正解データの範囲を同じ段落で限定する。

この方針は、技術報告書をfront matter、要約、本文、back matterへ分ける[IEEEの技術報告書ガイド](https://procomm.ieee.org/communication-resources-for-engineers/written-reports/write-effective-reports/)、方法と結果を分けて再現可能性を担保する[IEEEの研究報告ガイド](https://procomm.ieee.org/transactions-of-professional-communication/for-prospective-authors/guidelines-to-follow/preparing-research-reports-and-integrative-literature-reviews/)、重要な図表を本文中の言及直後へ置く[MITのTechnical Report Format](https://ocw.mit.edu/courses/3-014-materials-laboratory-fall-2006/cf3f5887f61b42c07e3764543d0169ba_w1_techrep_formt.pdf)に基づく。Wordでは組み込み見出しを論理順に用い、図へ代替テキストを付け、表に見出し行を設定する[Microsoftのアクセシビリティ指針](https://support.microsoft.com/en-US/accessibility/word/make-your-word-documents-accessible-to-people-with-disabilities)を適用する。図キャプションを図の下、表題を表の上に置く日本語技術文書の慣例は[長岡技術科学大学の技術文書ガイド](https://geotech1.nagaokaut.ac.jp/HTML/ipro/ex0402.html)に合わせる。

## 2. 課題文要求と報告書の対応

| 課題文の要求 | 本文での直接回答 | 付録の証拠 |
|---|---|---|
| 実験の仮説 | 第3章 | 実験条件・run ID一覧 |
| 実験結果 | 第8章 | 全コーパス詳細 |
| 試行錯誤の過程・発見 | 第3章、第9章 | 履歴ベイクオフ、失敗run |
| プロンプト | 第6章に要点 | 付録Aに全文または実行時構造 |
| ソースコード | 第6章に責務対応 | 付録Bに実コード3抜粋 |
| 最終出力結果 | 第9章に27行全表 | run ID、prediction artifact |
| 精度評価 | 第8章、第9章 | matched cohort、全コーパス詳細 |
| 技術的issueの分解 | 第2章、第10章 | コード監査・運用リスク |
| 不正解となったもの | 第10章 | 失敗runと分類表 |
| issueごとの解決見通し | 第10章 | 次回実験の詳細 |
| 他企業への汎用性 | 第8章 | 3M複数年度、日本10社、102 PDF |
| Google Docs提出 | Word完成後にGoogle Docsへ変換可能 | 変換前DOCXを正本として保持 |
| ローカルコード一式 | 本文では主要fileを案内 | repositoryを別フォルダとして提出 |

## 3. 最終の章構成

### 既存ページ（継承・整形）

1. **表紙** — 提出先、作成者、公開ページ、更新日。
2. **目次** — Wordの見出しスタイルから更新可能な目次。本文13章と付録を表示。
3. **課題概要** — 既存文章を維持し、進捗表現だけ「完了」に更新。

### 本文

#### 0. エグゼクティブサマリー

- 課題、方法、主要結果、結論を1ページで回答する。
- hero resultは「3M FY2022、同一run条件で27/27を維持し、Strategy 2比で入力tokenを96.1%削減」。
- 同時に「推論なしでは23/27」「matched 75 PDFでは最速とは限らない」を併記する。

#### 1. 課題文と受入条件

- 課題文を短く再掲する。
- 27行、2022年列、M USD、精度評価、他社汎用性、prompt/code、issue見通しを受入条件へ変換する。
- goldは推論後だけ使うという評価境界を明示する。

#### 2. 問題を三つに分解する

- 冒頭の問い: **「年次報告書から、指定された27項目の資産表を、他社にも適用できる形でどう作るか」**。
- 問いを下向き矢印で三つへ分ける。
  1. 年次報告書を大規模言語モデルが読める形にする。
  2. 年度・通貨・単位・固定27項目を正しく指示する。
  3. 出力契約、算術整合性、正解値によって評価する。
- **図1「問いから三つの技術境界への分解」**を掲載する。

#### 3. 初期仮説と設計変更

- H1: 全文を文字抽出して渡せば解ける。
- H2: 文字層不良は文字認識とレイアウト保持で改善できる。
- H3: 必要箇所の反復探索には能動的検索が有効である。
- 判断: 1 PDF、固定27項目、証拠が本表と限定注記に集中するため、検索思想だけを残し、決定論的ページ選択へ縮約する。
- **図2「仮説の進化と三戦略」**を掲載する。

#### 4. 三つの実験戦略

- Strategy 1: 同一4 parser、文字認識なし。
- Strategy 2: 同一4 parser、文字認識あり。ただしOCR engine差を含むため純粋ablationではない。
- Strategy 3: pdf-inspector、選択文字認識、全ページ採点、上位3〜5ページ、限定追試。
- 共通後段を固定し、入力表現の違いを比較する。

#### 5. 最終アーキテクチャと採用理由

- 入力固定、ページ解析、選択文字認識、決定論的ページ選択、意味写像、固定27行契約、算術検証、限定再試行、評価を説明する。
- 一般的なRAGを採用しなかった理由を、適用範囲、再現性、表の文脈、コスト、監査性で比較する。
- **図3「最終アーキテクチャ」**を掲載する。

#### 6. 実装と実験前提

- model、temperature、reasoning、currency、unit、PDF SHA、prompt、retry上限を示す。
- promptの要点を示すが、全文は付録へ移す。
- 実装責務表を掲載し、コード抜粋は付録Bへ誘導する。

#### 7. 評価方法

- Exact、Coverage、Precision、Consistency、token、time、completionを定義する。
- PDF screening、算術整合性、gold verificationの違いを説明する。
- matched cohort、macro/micro、partial goldの扱いを明示する。

#### 8. 実験結果

本文は次の四つに限定する。

1. 3M FY2022の3戦略同条件比較。
2. 3M FY2021〜FY2025。
3. 日本10社FY2022。
4. GLM推論ありのmatched 75 PDF。

102 PDFの全条件aggregate、Gemini credit失敗、旧45-arm parser bakeoffは付録へ移す。

#### 9. 最終27項目出力

- 最終採用run `S3_20260823T113348Z_001`の27行を全文掲載する。
- 列は「項目」「システム出力」「課題提供値」「判定」「根拠ページ」。
- 27/27、Exact 100%、Coverage 100%、Consistency 100%を表の直前に示す。
- この100%は、3M FY2022、GLM-5.3、temperature 0.0、推論あり、当該PDF SHAに限定する。

#### 10. 失敗分析とissueごとの解決見通し

| issue群 | 本文で扱う代表例 | 解決見通しの表現 |
|---|---|---|
| 入力表現 | 文字層破損、画像PDF、表の列順、必要注記漏れ | 高 / 中〜高。OCR routing、evidence recallで測る |
| 意味写像 | 年度列、会社固有科目、合算科目、0とnull | 中。LLMと一般化可能な語彙で改善、完全rule化はしない |
| 評価 | gold漏洩、PDF版違い、partial gold、生存者バイアス | 高。SHA固定、matched cohort、分母分離で制御 |
| 原資料の限界 | 非開示項目 | 解決不可。unscorableとして評価側で扱う |

#### 11. 現在の実装状況と既知の制約

- 1ページに限定する。
- 27行契約、Strategy 1/2/3、修復、算術検証、gold隔離、UI/API、主要検証を状態表で示す。
- 本番運用、認証、永続化、実費は未再検証または未対応と明示する。
- deployment bug、unused import、stale fileは本文へ置かない。

#### 12. 結論

- 最終採用理由を「常に最高精度」ではなく「精度を監視しながら入力を大幅削減し、選択根拠を再現・監査できる」とまとめる。
- 初期の三分解へ戻り、各境界を独立に扱ったことが主要な設計成果であると結ぶ。

#### 13. 次に行う実験

- held-out企業、evidence recall、反復実験、実費、共有OCR対照、confidence calibrationを優先順で示す。
- RAG再評価の条件を「複数文書横断、任意質問、固定スキーマ外」と定義する。

### 付録

- **付録A:** prompt全文と実験前提。
- **付録B:** 実コード3抜粋。
  1. `intelligent_scan.py`の3〜5ページ選択。
  2. `models.py`の27行・順序契約。
  3. `reconcile.py`の一意残差補完。
- **付録C:** 102 PDF全コーパス詳細、Gemini/GLM、旧45-arm。
- **付録D:** run ID、PDF SHA、再現command、主要file。
- **付録E:** codebase audit。確認済みbug、設計リスク、保守課題、stale data/file、提出不要生成物。
- **付録F:** 参考資料。

## 4. Word実装ルール

- Heading 1 → Heading 2 → Heading 3の順を崩さない。
- 目次はWordの見出しから更新可能にする。
- 本文はA4縦。横長の三図だけA4横の独立ページにする。
- 図は1600×900 PNGを使用し、元のHTML/SVG codeも同梱する。
- 図内テキストは日本語のみ。`PDF`、`LLM`、`OCR`、`JSON`等も本文図では「年次報告書」「大規模言語モデル」「文字認識」「固定形式」と表記する。
- 色だけで意味を伝えず、各箱に境界名と役割を書く。
- 全図に代替テキスト、全表に見出し行を設定する。
- 図キャプションは下、表題は上。図表は本文の最初の言及直後へ置く。
- 本文は14〜18ページ程度を目標とし、付録は別にする。情報量より課題への直接回答性を優先する。
