from flask import Flask, render_template, render_template_string, request, redirect, session, url_for, jsonify
from pymongo import MongoClient
from bson import ObjectId
import secrets, random

app = Flask(__name__)

# セッションの暗号キー
app.secret_key = secrets.token_bytes(10)

# mongoDB接続情報
mongoDBURL = "mongodb+srv://yu8sub:sub1175661@cluster0.nwhr0oa.mongodb.net/?retryWrites=true&w=majority"
client = MongoClient(mongoDBURL)
# DB接続情報
db_users = client.test.users
db_dict = client.test.dict
db_category = client.test.category
db_count = client.test.count


# @login_requiredデコレータの実装
# 関数呼び出し前にセッションを確認してNoneであればログイン画面にリダイレクトする
def login_required(func):
    import functools
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        if session.get("userId") is None:
            return redirect(url_for("login"))
        else:
            return func(*args, **kwargs)
    return wrapper

@app.route("/")
def index():
    return render_template("index.html")

@app.route('/login', methods=["POST", "GET"])
def login():

    #POSTかGETかで判別
    if request.method == "POST":
        # リクエストから値取得
        userId = request.form["userId"]
        password = request.form["password"]

        # DBから値取得
        user = db_users.find_one({"userId": userId, "password": password})

        # 判定
        if user:
            # セッションを保存
            session["userId"] = user["userId"]
            return render_template('main.html')
        else:
            return render_template('login.html', users=None)
    
    else:
        # 通常のログインフォームを表示
        return render_template("login.html")

@app.route('/main')
def main():
    return render_template("main.html")

@app.route('/addHash', methods=["GET", "POST"])
def add_hash():
    """DBにハッシュ値を登録する"""

    if request.method == "POST":
        action = request.form.get("action")
        
        if action == "generate":
            # ハッシュ値の生成
            hash_value = secrets.token_hex(4)  # 8桁のハッシュ値
            session["hash_value"] = hash_value  # セッションにハッシュ値を保存
            return render_template("addHash.html", hash_value=hash_value)

        elif action == "register":
            # ハッシュ値のデータベースへの登録
            hash_value = session.get("hash_value")
            if hash_value:
                userId = session.get("userId")
                # データベースのユーザー情報を更新
                db_users.update_one({"userId": userId}, {"$set": {"hash": hash_value}})
                return render_template("addHash.html", message="ハッシュ値を登録しました。")
            else:
                return render_template("addHash.html", error="ハッシュ値が生成されていません。")

    else:
        return render_template("addHash.html")

@app.route('/addCategory', methods=["GET", "POST"])
def add_category():
    """DBにカテゴリを登録する"""

    if request.method == "POST":
            
        # 語句と意味をフォームから取得
        # json形式で受け取る
        data = request.json
        category = data.get("category")
        
        if not category:
            response = jsonify(message="カテゴリを入力してください。")
            response.status_code = 400
            return response
        else:

            # 最大の連番を取得
            latest_word = db_category.find_one(sort=[("category_number", -1)])
            if latest_word:
                next_category_number = int(latest_word["category_number"].replace("category", "")) + 1
            else:
                next_category_number = 1

            # 新しいカテゴリを登録
            new_category = {
                "word_category": f"word{next_category_number}",
                "category": category
            }
            db_category.insert_one(new_category)

            current_category = list(db_category.find())

            return render_template(
                "addCategory.html", 
                message="新しいカテゴリを登録しました。", # 登録した語句の内容も表示したい
                categories=current_category
                )

    else:
        current_category = list(db_category.find())
        return render_template(
            "addCategory.html",
            categories=current_category
            )

@app.route('/registWord', methods=["GET", "POST"])
def regist_word():
    """語句リスト表示＆語句保存
    POSTの場合、語句保存
    GETの場合、語句一覧表示

    Returns:
        _type_: _description_
    """
    
    if request.method == "POST":
            
        # 語句と意味をフォームから取得
        # json形式で受け取る
        data = request.json
        word = data.get("word")
        word_mean = data.get("word_mean")
        word_category_id = data.get("word_category")
        
        if not word or not word_mean:
            response = jsonify(message="語句と語句の意味の両方を入力してください。")
            response.status_code = 400
            return response
        
        # カテゴリのObjectIdを検証
        try:
            category_object_id = ObjectId(word_category_id)
        except Exception as e:
            print(e)
            return jsonify(message="無効なカテゴリIDです。"), 400
        
        category = db_category.find_one({"_id": ObjectId(word_category_id)})
        
        if not category:
            print(category)
            return jsonify(message="カテゴリが見つかりません。"), 400
        else:
            # 最大の連番を取得
            latest_word = db_dict.find_one(sort=[("word_number", -1)])
            
            if latest_word:
                    next_word_number = int(latest_word["word_number"].replace("word", "")) + 1
            else:
                next_word_number = 1

            # 新しい語句を登録
            new_word = {
                "word_number": f"word{next_word_number}",
                "word": word,
                "word_mean": word_mean,
                "word_category": category_object_id
            }
            db_dict.insert_one(new_word)

            words = list(db_dict.find())
            category = list(db_category.find())

            return render_template(
                "registWord.html", 
                message="新しい語句を登録しました。", # 登録した語句の内容も表示したい
                words=words,
                word_category=category
                )      
    else:
        words = list(db_dict.find())
        category = list(db_category.find())
        
        return render_template(
            "registWord.html",
            message="",
            words=words,
            word_category=category
            )

@app.route('/saveCategoryChanges', methods=['POST'])
def save_category_changes():
    """カテゴリ変更保存

    Returns:
        json: success
    """
    data = request.json
    word_id = ObjectId(data['id'])
    category = data['category']
    
    # id取得確認
    print("word_id:", word_id)
    print("new_category:", category)

    # データベースを更新
    db_category.update_one({"_id": word_id}, {"$set": {"category": category}})

    return jsonify(success=True)

@app.route('/saveWordChanges', methods=['POST'])
def save_word_changes():
    """語句保存

    Returns:
        json: success
    """
    data = request.json
    word_id = ObjectId(data['id'])
    new_word = data['word']
    new_meaning = data['word_mean']
    new_category = ObjectId(data['word_category'])
    
    # id取得確認
    print("word_id:", word_id)
    print("new_word:", new_word)
    print("new_meaning:", new_meaning)
    print("new_category:", new_category)

    # データベースを更新
    db_dict.update_one({"_id": word_id}, {"$set": {"word": new_word, "word_mean": new_meaning, "word_category": new_category}})

    return jsonify(success=True)

@app.route('/saveAllWordChanges', methods=['POST'])
def save_all_word_changes():
    data = request.json
    words = data['words']
    
    for word_data in words:
        word_id = ObjectId(word_data['id'])
        new_word = word_data['word']
        new_meaning = word_data['word_mean']
        new_category = ObjectId(word_data['word_category'])

        db_dict.update_one({"_id": word_id}, {"$set": {"word": new_word, "word_mean": new_meaning, "word_category": new_category}})

    return jsonify(success=True)

@app.route('/deleteWord', methods=['POST'])
def delete_word():
    data = request.json
    word_id = ObjectId(data['id'])  # 文字列からObjectIdに変換

    # データベースからドキュメントを削除
    db_dict.delete_one({"_id": word_id})

    return jsonify(success=True)

@app.route('/deleteWords', methods=['POST'])
def deleteWords():
    data = request.json
    word_ids = data.get("word_ids")

    # word_idsに含まれる各IDに対応する語句を削除
    for word_id in word_ids:
        db_dict.delete_one({"_id": ObjectId(word_id)})

    return jsonify(success=True)


@app.route('/createQuestionMain')
def create_question_main():
    # 登録済みの単語数を取得
    words_count = db_dict.count_documents({})
    
    # セッションが存在するかチェック
    session_existence = 'question_index' in session and 'question_sets' in session
    
    return render_template(
        'createQuestionMain.html', 
        words_count=words_count,
        session_existence=session_existence
        )

@app.route('/solveQuestions', methods=["POST", "GET"])
def solve_problems():
    
    # 初めからの場合、セッションをクリア
    if request.method == "POST":
        session.clear()
        # 問題数を取得
        select_question_count = request.form.get('count', type=int)
        session['question_count'] = select_question_count
        print("問題数:", select_question_count)
    
    # セッションを確認
    if 'question_index' not in session:

        # MongoDBのコレクションから全単語を取得
        words = list(db_dict.find())

        # 出題する単語をランダムに選択
        selected_words = random.sample(words, select_question_count)
        print("selected_words", selected_words)     
        
        # 問題セットのリストを作成
        question_sets = []
        
        for question_word in selected_words:
            # 正解を含む選択肢リストを作成
            choices = [question_word['word_mean']]
            # 正解以外の選択肢を取得
            other_choices = [word['word_mean'] for word in words if word['_id'] != question_word['_id']]
            # 正解以外の選択肢からランダムに3つ選択して選択肢リストに追加
            choices.extend(random.sample(other_choices, 3))
            # 選択肢をシャッフル
            random.shuffle(choices)
            
            # 問題の正解/不正解数を取得
            count = get_count_answer(question_word['_id'])
            print("question_word_answer_count:", count)
            
            # 問題セットを追加
            question_sets.append({
                'question_word': question_word['word'],
                'question_word_id': str(question_word['_id']),
                'count_correct': count['count_correct'],
                'count_incorrect': count['count_incorrect'],
                'choices': choices,
                'correct': question_word['word_mean']
            })
        
        # sessionに格納
        session['question_sets'] = question_sets
        session['question_index'] = 0
    
    # 現在のインデックス
    current_question_index = session['question_index']
    # 現在のセッション
    current_session_question_count = session['question_count']
    # 現在の問題を取得してsolveQuestions.htmlを返す
    current_question_sets = session.get('question_sets', [])
    
    current_question = current_question_sets[current_question_index]

    return render_template(
            'solveQuestions.html', 
            question_sets=current_question,
            question_count=current_session_question_count,
            question_index=current_question_index
        )

@app.route('/submitAnswer', methods=['POST'])
def submit_answer():
    # 現在の問題インデックスを取得
    current_question_index = session.get('question_index', 0)
    current_question_sets = session.get('question_sets', [])

    if current_question_index < len(current_question_sets) - 1:
        # sessionのインデックスを更新
        session['question_index'] += 1
        print("sessionのindex:",session['question_index'])
        
        # 次の問題へ
        return redirect(url_for('solve_problems'))
    else:
        # 全ての問題が終了した場合、結果ページなどへリダイレクト
        # セッションを空にする
        session.clear()
        return redirect(url_for('create_question_main'))

@app.route('/solveQuestions', methods=['POST'])
def count_AnswerResult():
    data = request.json
    word_id = ObjectId(data['id'])
    answer_result = data['answerResult']
    print("word_id:", word_id)
    print("answer_result:", answer_result)
    
    try:
        check_record = db_count.find_one({
            'word_id': word_id
        })

        if answer_result:
            if check_record:
                # word_idを持つ既存のドキュメントが存在＆正解の場合
                new_count = check_record['count_correct'] + 1
                db_count.update_one(
                    {'word_id': word_id},
                    {'$set': {'count_correct': new_count}}
                )
            else:
                # word_idを持つ既存のドキュメントが存在しない＆正解の場合
                db_count.insert_one({
                'word_id': word_id,
                'count_correct': 1,
                'count_incorrect': 0
                })
        else:
            if check_record:
                # word_idを持つ既存のドキュメントが存在＆不正解の場合
                new_count = check_record['count_incorrect'] + 1
                db_count.update_one(
                    {'word_id': word_id},
                    {'$set': {'count_incorrect': new_count}}
                )
            else:
                # word_idを持つ既存のドキュメントが存在しない＆不正解の場合
                db_count.insert_one({
                'word_id': word_id,
                'count_correct': 0,
                'count_incorrect': 1
                })
                
    except Exception as e:
        print(e)
        
    return jsonify(success=True)
    
@app.route('/goBackToCreateQuestion')
def go_back_to_create_question():
    # createQuestionMain.htmlにリダイレクトする
    return redirect(url_for('create_question_main'))

@app.route('/logout')
def logout():
    session.clear()
    return render_template("index.html", message="ログアウトしました。")


def get_count_answer(word_id):
    """正解/不正解数を取得

    Args:
        word_id (str): 語句のおぶじぇくとID
    """
    try:
        obj_id = ObjectId(word_id)
        print("obj_id", obj_id)
    except Exception as e:
        return ("Invalid Object Format: ", e)
    
    target_record = db_count.find_one({"word_id": obj_id})
    print("target_record", target_record)
    
    if target_record:
        count_correct = target_record.get('count_correct', 0)
        count_incorrect = target_record.get('count_incorrect', 0)
        return {"count_correct": count_correct, "count_incorrect": count_incorrect}
    else:
        return {"count_correct": 0, "count_incorrect": 0}
        
        
        
    
    

if __name__ == '__main__':
    app.run(debug=True)
