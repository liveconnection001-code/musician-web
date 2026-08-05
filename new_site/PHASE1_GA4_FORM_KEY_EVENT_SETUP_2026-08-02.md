# GA4 お問い合わせ完了の計測設定案（第1段階）

## 結論

- 対象は自社所有プロパティ「MUSICIAN - GA4」、測定IDは `G-74ETNWY2T9`。
- お問い合わせの「入力画面を見た人」ではなく、「送信完了画面まで到達した人」を `generate_lead` として計測する。
- `generate_lead` は完了画面URL条件でGA4側に設定済み。サイト側は測定IDを全ページでこの自社所有IDに統一する。

## 現行フォームで使う完了条件

現行フォームは次の順に進む。

1. 入力画面: `/contact.html`
2. 確認画面: `/contact/postmail`
3. 送信完了画面: `/contact/postmail/thanks.html`

テンプレートとコントローラーを確認した結果、最終送信時だけ `thanks.html` テンプレートが表示される構造になっている。したがって、完了イベントは `page_view` のうち、ページパスが `/contact/postmail/thanks.html` と一致する場合に限定する。

完了URLは本番テストで `/contact/postmail/thanks.html` と確認済み。今後URL構造を変更した場合は、実測値を優先してGA4側の条件も同期する。

## GA4管理画面での設定手順

1. GA4で対象プロパティを開く。
2. 「管理」→「データの表示」→「イベント」を開く。
3. 「イベントを作成」を選ぶ。
4. カスタムイベント名を `generate_lead` とする。
5. 一致条件を次のように設定する。
   - `event_name` が `page_view` と等しい。
   - `page_location` が実測した完了URLと等しい。
     - 想定値: `https://www.musician.co.jp/contact/postmail/thanks.html`
   - 管理画面で `page_path` を選べる場合は、`/contact/postmail/thanks.html` との完全一致でもよい。
6. 元イベントのパラメータをコピーする設定を有効にして保存する。
7. 作成した `generate_lead` を「キーイベントとしてマーク」する。
8. キーイベントのカウント方法は、完了画面の再読み込みによる重複を抑えるため「セッションごとに1回」を第一候補とする。同一セッション内の複数問い合わせも個別に数える必要が生じた場合だけ「イベントごとに1回」へ変更する。

## 検証手順

1. 設定直後に、社内のテストと分かる内容でフォームを1回だけ正常送信する。
2. GA4のRealtimeで `page_view` と `generate_lead` が各1回記録されることを確認する。
3. DebugViewを使える場合は、完了画面で `generate_lead` が発火し、入力画面・確認画面では発火しないことを確認する。
4. 完了画面を再読み込みし、キーイベントが意図せず増えないことを確認する。
5. 翌日以降、標準レポートのキーイベントに `generate_lead` が表示されることを確認する。

## 誤計測を避ける条件

- `/contact.html` の閲覧を問い合わせ完了として数えない。
- `/contact/postmail` の確認画面を問い合わせ完了として数えない。
- URL条件に「`contact` を含む」のような広い条件を使わない。
- `page_view` 全体をキーイベントにしない。
- GA4でイベントを作成する前に、実際の完了URLを一度確認する。

## サイト側の測定ID差し替えで変更しないもの

- GA4管理画面のイベント・キーイベント設定（設定済みのため維持）
- Google広告へのコンバージョン取り込み
- `generate_lead` の完了画面URL条件
- フォーム項目、送信処理、完了画面の本文

## 参照した公式資料

- Google Analytics ヘルプ「推奨イベント」: `generate_lead` は、フォーム送信など見込み顧客の獲得を表す推奨イベント。
  - https://support.google.com/analytics/answer/9267735
- Google Analytics ヘルプ「キーイベントを作成または変更する」: 確認ページの `page_view` を条件に新しいイベントを作り、そのイベントだけをキーイベントにする手順。
  - https://support.google.com/analytics/answer/12844695
