## Requirements

* Awsアカウント

## Lambdaでの利用方法

1. Lambdaで利用するロールの作成
    1. IAMのロールページを開いて「ロールを作成」を選択。
    2. 「AWSのサービス」を選択して（デフォルト）、ユースケースで「Lambda」を選択して「次へ」
    3. 「許可を追加」の画面で、許可ポリシーでソ－ス内にある「roleに設定すべきポリシー」を追加する。今はおそらく
      - AWSLambdaBasicExecutionRole
      - AmazonSageMakerFullAccess
      - AmazonRedshiftFullAccess
      - ComprehendFullAccess
    4. ロール名を適当に入れて、「ロールを作成」をクリック
    
2. Lambda関数の作成
    1. Lambdaのページを開いて「関数の作成」を選択。
    2. 「一から作成」を選択し、適当な関数名を入力。ランタイムで「python3.9」。アーキテクチャで「x86_64」。実行ロールで「既存のロール」を選択して、上記の「1.」で作成したロールを選択して、「関数の作成」をクリック
    3. コードをlambda_function.pyにコピペ
    4. 設定タブの一般設定で「編集」をクリックして、タイムアウトを適当に大きくする10分くらい？
    5. Testをクリックして動くか確認。うまくいけばFunction Logsに動作中のリソースが表示される
