# Pokémon Lakehouse 実運用パイプライン設計

## 1. 目的

公式ポケモンカード大会データを毎日取得し、以下を自動更新する。

* 2026年以降の大会一覧
* 大会結果
* デッキコード
* デッキ内容
* カード採用率
* デッキ類似度
* アーキタイプ分類

基本方針は次の通り。

```text
Bronze：外部データの取得履歴
Silver：業務エンティティの最新状態
Gold：分析用集計・特徴量
ML：類似度・クラスタリング
```

---

## 2. 全体フロー

```text
Daily Pokémon Pipeline
│
├─ 01. Ingest Tournament List
│      公式大会一覧APIを取得
│
├─ 02. Merge Tournaments
│      大会ID単位でSilverへMERGE
│
├─ 03. Identify Result Fetch Targets
│      結果未取得・結果更新候補の大会を抽出
│
├─ 04. Ingest Tournament Results
│      対象大会の結果JSONを取得
│
├─ 05. Merge Tournament Results
│      順位・プレイヤー・デッキコードをSilverへMERGE
│
├─ 06. Identify Deck Fetch Targets
│      未取得・更新対象のdeck_codeを抽出
│
├─ 07. Ingest Deck HTML
│      公式デッキページHTMLを取得
│
├─ 08. Build Deck Silver
│      decks / deck_cardsを更新
│
├─ 09. Build Gold Analytics
│      card_usage / deck_registry / features
│
├─ 10. Build Similarity
│      デッキ類似度を更新
│
└─ 11. Build Archetypes
       クラスタリングを再実行
```

---

## 3. Databricks Workflow構成

Job名：

```text
Daily Pokémon Lakehouse Pipeline
```

推奨スケジュール：

```text
毎日 06:00 JST
```

公式サイトの更新が深夜から早朝に行われる想定で、朝の分析開始前に完了させる。

タスク依存関係：

```text
01_ingest_tournament_list
        ↓
02_merge_tournaments
        ↓
03_identify_result_targets
        ↓
04_ingest_event_results
        ↓
05_merge_tournament_results
        ↓
06_identify_deck_targets
        ↓
07_ingest_decks
        ↓
08_build_deck_silver
        ↓
09_build_gold_tables
        ↓
10_build_deck_similarity
        ↓
11_build_deck_archetypes
```

各タスクは独立したNotebookとして実装する。

---

## 4. Notebook一覧

### 01_ingest_tournament_list

```text
notebooks/01_ingest/00_ingest_tournament_list
```

入力：

```text
https://players.pokemon-card.com/event_search
```

出力：

```text
pokemon.bronze.tournament_list_raw
pokemon.bronze.tournament_list_scrape_log
```

処理：

* offsetを20ずつ増加
* 2026年以前だけのページに到達したら停止
* ページJSONを保存
* response_hashで同一ページ内容を重複保存しない

再実行特性：

```text
安全
```

同じレスポンスは再保存されない。

---

### 02_merge_tournaments

```text
notebooks/02_silver/01_build_tournaments
```

入力：

```text
pokemon.bronze.tournament_list_raw
```

出力：

```text
pokemon.silver.tournaments
```

粒度：

```text
1行 = 1 tournament_id
```

処理：

* `event`配列を展開
* 2026年以降に限定
* event_hashを計算
* tournament_idでMERGE
* 新規大会はINSERT
* 内容変更時のみUPDATE

再実行特性：

```text
安全
```

---

### 03_identify_result_targets

```text
notebooks/02_silver/02_identify_result_fetch_targets
```

目的：

大会結果APIを取得すべき大会だけを抽出する。

候補条件：

```text
Silver tournamentsに存在する
AND
結果取得対象の大会である
AND
次のいずれか
  - Bronzeに結果が存在しない
  - 前回結果取得時から大会情報が更新された
  - 前回レスポンスが空だった
  - 前回取得に失敗した
```

出力方法：

初期段階では一時Viewでよい。

```text
result_fetch_targets
```

将来的には運用監視用テーブルを作る。

```text
pokemon.ops.result_fetch_queue
```

推奨列：

```text
tournament_id
event_date
event_title
fetch_reason
last_result_fetched_at
priority
```

---

### 04_ingest_event_results

```text
notebooks/01_ingest/01_ingest_event_results
```

入力：

```text
result_fetch_targets
```

出力：

```text
pokemon.bronze.event_result_raw
pokemon.bronze.scrape_log
```

粒度：

```text
1行 = 1 tournament_id × 1レスポンスバージョン
```

処理：

* 対象tournament_idを順番に取得
* JSONをRaw保存
* response_hashで同一レスポンスを重複排除
* HTTPステータスとエラーを記録
* API負荷軽減のためリクエスト間隔を設定

重要：

大会一覧に掲載された直後は、結果がまだ空の場合がある。

そのため「一度取得したら二度と取得しない」ではなく、状態を分ける。

```text
success_with_results
success_empty
error
skipped_unchanged
```

`success_empty`は後日再取得対象にする。

---

### 05_merge_tournament_results

```text
notebooks/02_silver/02_build_tournament_results
```

入力：

```text
pokemon.bronze.event_result_raw
```

出力：

```text
pokemon.silver.tournament_results
```

粒度：

```text
1行 = tournament_id × result_rank
```

または、プレイヤーIDが存在する場合：

```text
1行 = tournament_id × player_id
```

処理：

* 最新の結果レスポンスを選択
* 順位・プレイヤー・デッキコードを展開
* 結果レコード単位のhashを作成
* MERGEで更新

一意キー候補：

```text
tournament_id
rank
player_id
```

実データでplayer_idの安定性を確認して決定する。

---

### 06_identify_deck_targets

```text
notebooks/02_silver/03_identify_deck_fetch_targets
```

目的：

未取得のdeck_codeだけを抽出する。

基本条件：

```sql
SELECT DISTINCT
    result.deck_code
FROM pokemon.silver.tournament_results result

LEFT ANTI JOIN (
    SELECT DISTINCT deck_code
    FROM pokemon.bronze.deck_raw
    WHERE status = 'success'
) deck

ON result.deck_code = deck.deck_code

WHERE result.deck_code IS NOT NULL
```

出力：

```text
deck_fetch_targets
```

再取得条件も用意する。

```text
未取得
前回取得失敗
HTMLパース失敗
手動再取得指定
```

---

### 07_ingest_decks

```text
notebooks/01_ingest/02_ingest_decks
```

入力：

```text
deck_fetch_targets
```

出力：

```text
pokemon.bronze.deck_raw
pokemon.bronze.scrape_log
```

粒度：

```text
1行 = 1 deck_code × 1 HTMLバージョン
```

処理：

* 公式デッキページを取得
* HTMLをそのまま保存
* response_hashで差分判定
* 成功・失敗を記録

通常、deck_codeの内容は不変と考えられるため、成功取得済みコードは原則再取得しない。

---

### 08_build_deck_silver

```text
notebooks/02_silver/03_build_decks
notebooks/02_silver/04_build_deck_cards
```

入力：

```text
pokemon.bronze.deck_raw
```

出力：

```text
pokemon.silver.decks
pokemon.silver.deck_cards
```

処理：

* HTMLをパース
* カテゴリ見出しを完全一致で判定
* 同名カードを正規化
* canonical_stringを生成
* deck_hashを計算
* deck_code単位でMERGE

データ品質チェック：

```text
デッキ合計枚数
必須カテゴリの存在
card_nameのNull
quantityの範囲
deck_hashの再現性
```

---

### 09_build_gold_tables

```text
notebooks/03_gold/
```

更新順：

```text
01_build_card_usage
02_build_deck_registry
03_build_deck_pokemon_features
```

出力：

```text
pokemon.gold.card_usage
pokemon.gold.deck_registry
pokemon.gold.deck_pokemon_features
```

初期運用では全件再構築でよい。

理由：

* 数百〜数千デッキ規模では十分軽い
* 複雑な増分集計より正確性を優先できる
* パイプライン設計が単純になる

データ量が大きくなった段階で増分化する。

---

### 10_build_deck_similarity

```text
notebooks/03_gold/04_build_deck_similarity
```

入力：

```text
pokemon.gold.deck_pokemon_features
```

出力：

```text
pokemon.gold.deck_similarity
```

注意点：

デッキ数をNとすると、組み合わせ数は次になる。

```text
N × (N - 1) ÷ 2
```

デッキ数の増加により急激に計算量が増える。

運用方針：

```text
〜1,000 deck_hash
全ペア再計算

1,000〜10,000 deck_hash
新規deck_hash対既存deck_hashだけ増分計算

10,000以上
近似最近傍検索を検討
```

当面は全再計算でよいが、実行時間を必ずログへ残す。

---

### 11_build_deck_archetypes

```text
notebooks/05_ml/01_cluster_deck_archetypes
```

入力：

```text
pokemon.gold.deck_similarity
pokemon.gold.deck_registry
pokemon.gold.deck_pokemon_features
```

出力：

```text
pokemon.gold.deck_archetypes
```

毎日再計算する必要は必ずしもない。

推奨条件：

```text
新規deck_hashが一定数以上追加された
新しい大会結果が追加された
週次スケジュール
```

初期フェーズでは、毎日実行しても問題ない。

安定運用後は週1回へ変更する。

---

## 5. 日次処理と週次処理の分離

### 日次

```text
大会一覧取得
大会一覧MERGE
結果対象抽出
大会結果取得
大会結果MERGE
デッキ対象抽出
デッキ取得
Deck Silver更新
Gold基本集計
```

### 週次

```text
全デッキ類似度再計算
アーキタイプ再学習
クラスタ品質評価
```

ただし、学習フェーズ中は全処理を毎日実行してもよい。

---

## 6. 更新判定の責務

### 大会一覧

```text
Bronze：response_hash
Silver：tournament_id + event_hash
```

### 大会結果

```text
Bronze：tournament_id + response_hash
Silver：結果レコードの一意キー + result_hash
```

### デッキHTML

```text
Bronze：deck_code + response_hash
Silver：deck_code + deck_hash
```

### Gold

```text
Silverの最新状態から再生成
```

---

## 7. 失敗時の再実行設計

各Notebookは冪等にする。

```text
同じNotebookを複数回実行しても
重複レコードを作らない
```

### Bronze取得失敗

* 成功済みレスポンスは残す
* エラーをログへ保存
* Jobを失敗扱いにする
* 次回または手動で再実行

### Silver失敗

* Bronzeは残っている
* Silver Notebookだけ再実行可能

### Gold・ML失敗

* Bronze・Silverは正常
* 失敗したGold以降だけ再実行可能

そのため、Databricks Workflowでは各レイヤーを別タスクにする。

---

## 8. Jobパラメータ

Notebook内へ値を直接書かず、Jobパラメータとして渡せるようにする。

推奨パラメータ：

```text
min_event_date = 2026-01-01
request_interval_seconds = 1.0
max_pages = 200
force_refetch = false
rebuild_gold = true
rebuild_similarity = true
rebuild_archetypes = true
```

手動復旧時には次のように変更できる。

```text
force_refetch = true
tournament_id = 1162
```

---

## 9. 運用ログ

既存のscrape_logに加え、パイプライン実行単位のログを持つ。

推奨テーブル：

```text
pokemon.ops.pipeline_run_log
```

粒度：

```text
1行 = 1 Job実行 × 1タスク
```

列：

```text
pipeline_run_id
job_run_id
task_name
status
started_at
finished_at
elapsed_ms
input_count
insert_count
update_count
skip_count
error_count
error_message
```

これにより、次の確認ができる。

```text
今日は新規大会が何件あったか
結果取得に何件失敗したか
新しいデッキが何件追加されたか
Similarityに何分かかったか
```

---

## 10. 通知設計

Job全体が失敗した場合：

```text
Slackまたはメール通知
```

通知内容：

```text
Job名
実行日時
失敗タスク
エラー概要
Databricks Run URL
取得成功件数
失敗件数
```

成功時は毎日通知せず、次の場合だけ通知する。

```text
新規大会が追加された
新規デッキが追加された
エラーが発生した
クラスタ数や品質指標が大きく変化した
```

---

## 11. 初期実装の優先順位

### Phase 1：自動収集

```text
1. 結果取得対象抽出
2. 複数大会結果取得
3. 未取得デッキ抽出
4. 複数デッキ取得
```

### Phase 2：パイプライン化

```text
5. Databricks Workflow作成
6. 日次スケジュール
7. タスク依存関係
8. リトライ・通知
```

### Phase 3：分析更新

```text
9. Goldの自動再構築
10. Similarity更新
11. Archetype更新
```

---

## 12. 次に実装するNotebook

最優先は次。

```text
notebooks/02_silver/
└── 02_identify_result_fetch_targets
```

このNotebookでは、以下を抽出する。

```text
新規大会
結果未取得大会
前回結果が空だった大会
前回取得が失敗した大会
```

出力は一時View：

```text
result_fetch_targets
```

その後、既存の大会結果取得Notebookを、固定のtournament_idではなく、この対象一覧を処理する形へ変更する。
