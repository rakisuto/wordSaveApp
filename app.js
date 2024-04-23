<script>
const app = new Vue({
  el: "#app",
  data: {
    message: "",
  },
  methods: {
    handleSubmit() {
      // フロントで入力された文字を取得する
      const message = this.message;

      // サーバ側にリクエストを送信する
      const axios = require("axios");
      const response = axios.post("/api/message", { message });

      // サーバ側からの応答を取得する
      const result = response.data;

      // フロントにメッセージを表示する
      this.message = result.message;
    },
  },
});
</script>
