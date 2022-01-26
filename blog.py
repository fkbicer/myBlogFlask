from typing import Text
from flask import Flask,render_template,flash,redirect,url_for,session,logging,request
from flask_mysqldb import MySQL
from wtforms import Form,StringField,TextAreaField,PasswordField,validators
from passlib.handlers.sha2_crypt import sha256_crypt
from functools import wraps

#Kullanıcı Giris Decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "logged_in" in session:
            return f(*args, **kwargs)
        else:
            flash("Bu sayfayi görüntülemek icin lutfen giris yapın.", "danger")
            return redirect(url_for("login"))
    return decorated_function
#Kullanıcı kayit formu
class RegisterForm(Form):
    name = StringField("İsim Soyisim",validators=[validators.Length(min=4,max=25)])
    username = StringField("Kullanıcı Adı",validators=[validators.Length(min=4,max=35)])
    email = StringField("email adres",validators=[validators.Email(message="Lutfen dgecerli bir email adresi giriniz.")])
    password = PasswordField("Parola:",validators=[validators.DataRequired(message="lutfen bir parola giriniz."),validators.EqualTo(fieldname="confirm")])
    confirm = PasswordField("Parola Dogrula")
class LogingForm(Form):
    username = StringField("Kullanıcı Adı")
    password = PasswordField("Sifre: ")
app= Flask(__name__)
app.secret_key="ybblog" #flash mesajlarını yayınlayabilmemiz icin secret_key'e ihtiyacımız var.

app.config["MYSQL_HOST"]="localhost"
app.config["MYSQL_USER"]="root"
app.config["MYSQL_PASSWORD"]=""
app.config["MYSQL_DB"]="ybblog"
app.config["MYSQL_CURSORCLASS"]="DictCursor"    

mysql= MySQL(app)
@app.route("/")
def index():
    articles=[
        {"id":1,"title":"deneme1","icerik":"icerik1"},
        {"id":2,"title":"deneme2","icerik":"icerik2"},
        {"id":3,"title":"deneme3","icerik":"icerik3"}
    ]   
    return render_template("index.html", articles = articles)
@app.route("/about")    
def about():
    return render_template("about.html")
@app.route("/dashboard")
@login_required
def dashboard():
    cursor = mysql.connection.cursor()
    sorgu = "Select * From articles where author = %s"
    result = cursor.execute(sorgu,(session["username"],))

    if result >0:
        articles = cursor.fetchall()
        return render_template("dashboard.html", articles = articles)
    else:
        return render_template("dashboard.html")


@app.route("/register",methods =["GET","POST"])
def register():
    form = RegisterForm(request.form)

    if request.method  == "POST" and form.validate():
        name = form.name.data
        username=form.username.data
        email=form.email.data
        password=sha256_crypt.encrypt(form.password.data)

        cursor = mysql.connection.cursor() #db'de işlem yapmak için cursor olusturduk
        sorgu = "Insert into users(name,email,username,password) VALUES(%s,%s,%s,%s)" #db'ye veri eklemek icin sql query calistiricaz
        cursor.execute(sorgu,(name,email,username,password)) #query'i burada execute ediyoruz
        mysql.connection.commit() #db'de yaptigimiz degisiklikleri kaydetmek icin commitliyoruz.
        cursor.close()
        flash("Basari ile kayit oldunuz...","success") #hemen bir sonraki request'de bir flash mesajı patlatıcaz.
        return redirect(url_for("login"))
    else:
        return render_template("register.html",form=form)
# Login islemi
@app.route("/login", methods= ["GET","POST"])
def login():
    form = LogingForm(request.form)
    if request.method == "POST":
        username = form.username.data
        passwowrd_entered = form.password.data
        cursor = mysql.connection.cursor()
        sorgu = "Select * From users where username = %s"
        result = cursor.execute(sorgu,(username,))
        if result > 0:
            data = cursor.fetchone()
            real_password = data["password"]
            if sha256_crypt.verify(passwowrd_entered,real_password):
                flash("Basarili bir sekilde giris yaptınız","success")
                session["logged_in"] = True # giris ve cıkıslari takip etmek icin session olusturuyoruz.
                session["username"] = username
                return redirect(url_for("index"))
            else:
                flash("Yanlis sifre girdiniz","danger")
                return redirect(url_for("login"))
        else:
            flash("Böyle bir kullanıcı bulunmuyor","danger")
            return redirect(url_for("login"))
        
    return render_template("login.html",form = form)   
#Logout islemi
@app.route("/logout")
def logout():
    session.clear() # giris yaparken yaratmız oldugumuz session'u öldürüyoruz.
    return redirect(url_for("index"))
#Makale Detay Sayfasi
@app.route("/article/<string:id>")
def article(id):
    cursor = mysql.connection.cursor()
    sorgu = "SELECT * FROM articles where id = %s"
    result = cursor.execute(sorgu,(id,))

    if result > 0:
        article = cursor.fetchone()
        return render_template("article.html", article = article)
    else:
        return render_template("article.html")
#Makale Sayfasi
@app.route("/articles")
def articles():
    cursor = mysql.connection.cursor()
    sorgu = "SELECT * FROM articles"
    result = cursor.execute(sorgu)

    if result > 0:
        articles = cursor.fetchall() #veritabanında bulunan verileri liste icinde sözlük olarak elde ediyoruz.      
        return render_template("articles.html",articles = articles)
    else:
        return render_template("articles.html")
#Makale Ekleme
@app.route("/addarticle",methods =["GET","POST"])
def addarticle():
    form = ArticleForm(request.form) #ArticleForm class'indan bir tane obje olusturuyoruz. bu objeyi request.form ile cekiyoruz.
    if request.method == "POST" and form.validate():
        title = form.title.data
        content = form.content.data

        cursor = mysql.connection.cursor()
        sorgu = "INSERT INTO articles(title,author,content) VALUES(%s,%s,%s)"
        cursor.execute(sorgu,(title,session["username"],content))
        mysql.connection.commit() #veritabanında herhangi bir degisiklik yapıldıgı zaman kaydedilmesi icin commit edilmesi gerekir.
        cursor.close() #islem sonrasi veritabanını kapatmak icin
        flash("Makale basarili bir sekilde eklendi.", "success")
        return redirect(url_for("dashboard"))
    return render_template("addarticle.html",form = form) # olusturdugumuz 'form' objesini gönderiyoruz.
#Makale Silme
@app.route("/delete/<string:id>")
@login_required
def delete(id):
    cursor = mysql.connection.cursor()
    sorgu ="SELECT * FROM articles where author = %s and id = %s "
    result=cursor.execute(sorgu,(session["username"],id))

    if result > 0:
        sorgu2 = "DELETE FROM articles where id = %s"
        cursor.execute(sorgu2,(id,))
        mysql.connection.commit() #veritabanını degistiren bir hamle oldugu icin commit yapıyoruz.
        return redirect(url_for("dashboard"))
    else:
        flash("Bu makaleyi silmeye yetkiniz bulunmamaktadır.","danger")
        return redirect(url_for("index"))
#Makale Güncelleme
@app.route("/edit/<string:id>",methods =["GET","POST"])
@login_required
def update(id):
    if request.method == "GET":
        cursor = mysql.connection.cursor()
        sorgu= "SELECT * FROM articles where id = %s and author = %s"
        result = cursor.execute(sorgu,(id,session["username"]))

        if result == 0:
            flash("Böyle bir makale yok yahut bu işleme yetkiniz yok","danger")
            return redirect(url_for("index"))
        else:
            article = cursor.fetchone() #burada güncelle butonuna basip get request ile yeni bir sayfada var olan form'u acmamiz gerekiyor
            form = ArticleForm() #yeni bir form olusturduk ve form icerisinde fetchone ile aldigimiz article'ın verilerini yerlestiriyoruz.
            form.title.data = article["title"]
            form.content.data=article["content"]
            return render_template("update.html",form = form)
    else: #POST REQUEST
        form = ArticleForm(request.form)

        newTitle = form.title.data
        newContent = form.content.data

        sorgu2 = "UPDATE articles SET title = %s, content =%s where id = %s"
        cursor = mysql.connection.cursor()
        cursor.execute(sorgu2,(newTitle,newContent,id))
        mysql.connection.commit()
        flash("makale basari ile güncellendi","success")
        return redirect(url_for("dashboard"))


#Makale Olusturma
class ArticleForm(Form):
    title = StringField("Makale Basligi",validators=[validators.Length(min=5, max = 100)])
    content = TextAreaField("Makale icerigi", validators=[validators.Length(min = 10)])
if __name__ == "__main__":
    app.run(debug=True)

