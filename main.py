import datetime
import os
import werkzeug
from flask import Flask, render_template, request, redirect, url_for
from flask_wtf import FlaskForm
from werkzeug.security import generate_password_hash, check_password_hash
from wtforms import StringField, SubmitField, FileField, PasswordField, IntegerField
from wtforms.validators import DataRequired, Email, Length, InputRequired
from flask_bootstrap import Bootstrap5
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Integer, String, Float, Boolean
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from pydifact.segmentcollection import Interchange
from pydifact.segments import Segment

logged_in = False
username = ""

app = Flask(__name__)
app.secret_key = "naEW#y0Y7EN00789ewry9pMEWRH"
bootstrap = Bootstrap5(app)
app.config['UPLOAD_FOLDER'] = 'static'  # sets ./static as default folder to save files


class Base(DeclarativeBase):
    pass


db = SQLAlchemy(model_class=Base)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///library.db"
db.init_app(app)


class Books(db.Model):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    author: Mapped[str] = mapped_column(String, nullable=False)
    availability: Mapped[int] = mapped_column(Integer, nullable=False)
    cover: Mapped[str] = mapped_column(String, nullable=True)


class Ratings(db.Model):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    book_id: Mapped[int] = mapped_column(Integer, nullable=False)
    rating: Mapped[int] = mapped_column(Integer, nullable=True)
    review: Mapped[str] = mapped_column(String, nullable=True)
    review_author: Mapped[str] = mapped_column(String, nullable=True)


class Users(db.Model):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_name: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    password: Mapped[str] = mapped_column(String, nullable=False)
    balance: Mapped[float] = mapped_column(Float, nullable=False)


class Borrowings(db.Model):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    book_id: Mapped[int] = mapped_column(Integer, nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    borrow_date: Mapped[str] = mapped_column(String, nullable=False)
    borrowed_for_days: Mapped[int] = mapped_column(Integer, nullable=False)
    borrow_returned: Mapped[bool] = mapped_column(Boolean, nullable=False)
    return_date: Mapped[str] = mapped_column(String, nullable=True)


class Fees(db.Model):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    borrow_id: Mapped[int] = mapped_column(Integer, nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    deadline: Mapped[str] = mapped_column(String, nullable=False)
    already_paid: Mapped[bool] = mapped_column(Boolean, nullable=False)


with app.app_context():
    db.create_all()


class AddingForm(FlaskForm):
    title = StringField(label="Title", validators=[DataRequired()])
    author = StringField(label="Author", validators=[DataRequired()])
    availability = IntegerField(label="Availability (pcs)", validators=[InputRequired()])
    cover = FileField(label="Cover picture")
    submit = SubmitField(label="Add product")


class LoggingForm(FlaskForm):
    user_name = StringField(label="E-mail", validators=[DataRequired(), Email()])
    password = PasswordField(label="Password", validators=[DataRequired(), Length(min=3)])
    submit = SubmitField(label="Log in")


class RegistrationForm(FlaskForm):
    user_name = StringField(label="E-mail", validators=[DataRequired(), Email()])
    password = PasswordField(label="Password", validators=[DataRequired(), Length(min=3)])
    submit = SubmitField(label="Register")


class EDIForm(FlaskForm):
    edi_string = StringField(label="EDI format invoice", validators=[DataRequired()])
    submit = SubmitField(label="Convert")


@app.route('/')
def home():
    global logged_in
    global username
    if not logged_in:
        msg = "Welcome to OnlineLibrary. Log in or register to borrow books."
    else:
        msg = ""
    book_list = db.session.execute(db.select(Books)).scalars()
    return render_template("index.html", products=book_list, x=logged_in, u=username,
                           msg=msg)


@app.route('/invoice_converter', methods=["POST", "GET"])
def invoice_converter():
    global logged_in
    global username
    form = EDIForm()
    if logged_in and request.method == "POST" and form.validate_on_submit():
        invoice_data = Interchange.from_str(form.edi_string.data)
        invoice_number = ""
        borrow_date = ""
        user = ""
        amount = None
        now = datetime.datetime.now().strftime("%d-%m-%y")
        for segment in invoice_data.segments:
            if segment.tag == "UNG":
                invoice_number = segment.elements[0][1]
            if segment.tag == "DTM":
                borrow_date = segment.elements[0][1]
            if segment.tag == "NAD":
                user = segment.elements[0][2]
            if segment.tag == "MOA":
                amount = segment.elements[0][1]
        return render_template("invoice.html", now=now,
                               invoice_number=invoice_number, borrow_date=borrow_date,
                               user=user, amount=amount)
    if not logged_in:
        return render_template("converter.html", msg="Remember about logging in first!",
                               form=form, x=logged_in, u=username)
    return render_template("converter.html", form=form, x=logged_in, u=username)


@app.route('/login', methods=["POST", "GET"])
def login():
    global logged_in
    global username
    form = LoggingForm()
    if not logged_in and request.method == "POST":
        if form.validate_on_submit():  # returns true only after proper form filling
            users = db.session.execute(db.select(Users)).scalars()  # admin
            user_email = form.user_name.data
            user_password = form.password.data
            for user in users:
                if (user_email == user.user_name) and (check_password_hash(user.password, user_password)):
                    username = user.user_name
                    logged_in = True
                    product_list = db.session.execute(db.select(Books)).scalars()
                    return render_template("index.html", msg="You have been logged in",
                                           products=product_list, x=logged_in, u=username)
            product_list = db.session.execute(db.select(Books)).scalars()
            return render_template("index.html", msg="Incorrect logging data provided",
                                   products=product_list, x=logged_in, u=username)
        else:
            product_list = db.session.execute(db.select(Books)).scalars()
            return render_template("index.html", msg="Incorrect logging data provided",
                                   products=product_list, x=logged_in, u=username)
    if logged_in:
        return render_template("denied.html", msg="You are already logged in", x=logged_in, u=username)
    return render_template("login.html", form=form, x=logged_in, u=username)


@app.route('/register', methods=["POST", "GET"])
def register():
    global logged_in
    global username
    form = RegistrationForm()
    if not logged_in and request.method == "POST":
        if form.validate_on_submit():
            users = db.session.execute(db.select(Users)).scalars()
            for u in users:
                if u.user_name == form.user_name.data:
                    return render_template("denied.html",
                                           msg="We already have user registered for this E-mail!",
                                           x=logged_in, u=username)
            user = Users(
                user_name=form.user_name.data,
                password=werkzeug.security.generate_password_hash(form.password.data, method='scrypt', salt_length=16),
                balance=0
            )
            db.session.add(user)
            db.session.commit()
            logged_in = True
            username = user.user_name
            book_list = db.session.execute(db.select(Books)).scalars()
            return render_template("index.html", msg="You have been registered",
                                   products=book_list, x=logged_in, u=username)
        else:
            product_list = db.session.execute(db.select(Books)).scalars()
            return render_template("index.html", msg="Incorrect data provided!",
                                   products=product_list, x=logged_in, u=username)
    if logged_in:
        return render_template("denied.html",
                               msg="To register new account, log out from current one first!",
                               x=logged_in, u=username)
    return render_template("register.html", form=form, x=logged_in, u=username)


@app.route("/add", methods=["POST", "GET"])
def add():
    global logged_in
    global username
    if logged_in and username == "admin@email.com":
        form = AddingForm()
        if form.validate_on_submit():
            cover_picture = form.cover.data
            if cover_picture:
                file_name = werkzeug.utils.secure_filename(cover_picture.filename)
                cover_picture.save(os.path.join(app.config['UPLOAD_FOLDER'], file_name))  # file saved in ./static
            else:
                file_name = "default.jpg"
            book = Books(
                title=form.title.data,
                author=form.author.data,
                availability=form.availability.data,
                cover=file_name
            )
            db.session.add(book)
            db.session.commit()
            return redirect(url_for("home"))
        return render_template("add.html", form=form, x=logged_in, u=username)
    else:
        return render_template("denied.html", msg="Only administrator can do it!",
                               x=logged_in, u=username)


@app.route("/borrow_list", methods=["POST", "GET"])
def borrow_list():
    global logged_in
    global username
    if logged_in:
        product_list = db.session.execute(db.select(Books)).scalars()
        return render_template("borrow_list.html", products=product_list, x=logged_in, u=username)
    else:
        return render_template("denied.html", msg="In order to do it, you need to be logged in!",
                               x=logged_in, u=username)


@app.route("/edit", methods=["GET", "POST"])
def borrow():
    global logged_in
    global username
    user = None
    if logged_in and request.method == "POST":
        if "cancel" in request.form:
            return redirect(url_for("home"))

        book_id = int(request.form["id"])
        book = db.get_or_404(Books, book_id)
        users = db.session.execute(db.select(Users)).scalars()
        for the_user in users:
            if the_user.user_name == username:
                user = db.get_or_404(Users, the_user.id)
        if user and book:
            borrowed = db.session.execute(db.select(Borrowings)).scalars()
            for tome in borrowed:
                if not tome.borrow_returned and tome.user_id == user.id and tome.book_id == book.id:
                    return render_template("denied.html",
                                           msg="You already have that book borrowed now!",
                                           x=logged_in, u=username)
            borrowing = Borrowings(
                book_id=book.id,
                user_id=user.id,
                borrow_date=datetime.datetime.now().strftime("%d.%m.%Y"),
                borrowed_for_days=1,
                borrow_returned=False
            )
            db.session.add(borrowing)
            book.availability -= 1
            # print(book.availability)
            db.session.commit()
            # print(book.availability)

            fee = Fees(
                user_id=user.id,
                borrow_id=borrowing.id,
                amount=0,
                deadline=(datetime.datetime.now() +
                          datetime.timedelta(days=borrowing.borrowed_for_days)).strftime("%d-%m-%y"),
                already_paid=False,
            )
            db.session.add(fee)
            db.session.commit()
            return render_template("denied.html", msg="Book successfully borrowed!", x=logged_in,
                                   u=username)
        else:
            return render_template("denied.html", msg="Borrowing failed!", x=logged_in,
                                   u=username)
    if not logged_in:
        return render_template("denied.html", msg="In order to do it, you need to be logged in!",
                               x=logged_in, u=username)
    product_id = request.args.get('id')
    product_selected = db.get_or_404(Books, product_id)
    return render_template("borrow.html", product=product_selected, x=logged_in, u=username)


@app.route("/return_list", methods=["POST", "GET"])
def return_list():
    global logged_in
    global username
    product_list = []
    user = None
    if logged_in:
        users = db.session.execute(db.select(Users)).scalars()
        for selected_user in users:
            if selected_user.user_name == username:
                user = db.get_or_404(Users, selected_user.id)
        borrowed = db.session.execute(db.select(Borrowings)).scalars()
        for borrowed_book in borrowed:
            if not borrowed_book.borrow_returned and borrowed_book.user_id == user.id:
                book_id = borrowed_book.book_id
                book = db.get_or_404(Books, book_id)
                product_list.append(book)
        return render_template("return_list.html", products=product_list, x=logged_in, u=username)
    else:
        return render_template("denied.html", msg="In order to do it, you need to be logged in!",
                               x=logged_in, u=username)


@app.route("/return_book", methods=["GET", "POST"])
def return_book():
    global logged_in
    global username
    if logged_in and request.method == "POST":
        if "cancel" in request.form:
            return redirect(url_for("home"))

        book_id = int(request.form["id"])
        book = db.get_or_404(Books, book_id)
        users = db.session.execute(db.select(Users)).scalars()
        user_id = None
        for chosen_user in users:
            if chosen_user.user_name == username:
                user_id = chosen_user.id
        if book_id and user_id:
            borrowed = db.session.execute(db.select(Borrowings)).scalars()
            for chosen_book in borrowed:
                if (not chosen_book.borrow_returned and chosen_book.user_id == user_id and
                        chosen_book.book_id == book_id):
                    borrowing_id = chosen_book.id
                    book_to_return = db.get_or_404(Borrowings, borrowing_id)
                    book_to_return.borrow_returned = True
                    book_to_return.return_date = datetime.datetime.now().strftime("%d-%m-%y")
                    book.availability += 1
                    db.session.commit()
                    return render_template("denied.html", msg="Book successfully returned!",
                                           x=logged_in, u=username)
            return render_template("denied.html", msg="Failed!", x=logged_in, u=username)
        else:
            return render_template("denied.html", msg="Failed to return the book!",
                                   x=logged_in, u=username)
    if not logged_in:
        return render_template("denied.html", msg="In order to do it, you need to be logged in!",
                               x=logged_in, u=username)
    product_id = request.args.get('id')
    product_selected = db.get_or_404(Books, product_id)
    return render_template("return_book.html", product=product_selected, x=logged_in, u=username)


@app.route('/my_history')
def my_history():
    global logged_in
    global username
    borrows_list = []
    if logged_in:
        user = db.session.execute(db.select(Users).where(Users.user_name == username)).scalar()
        borrows = db.session.execute(
            db.select(Borrowings).where(Borrowings.user_id == user.id and Borrowings.borrow_returned)).scalars()
        for wyp in borrows:
            book = db.get_or_404(Books, wyp.book_id)
            borrows_list.append([book.author, book.title, book.cover, wyp.borrow_date, wyp.return_date])
    return render_template("my_history.html", my_borrowings=borrows_list, x=logged_in, u=username)


@app.route('/invoices')
def invoices():
    global logged_in
    global username
    payments_list = []
    if logged_in:
        user = db.session.execute(db.select(Users).where(Users.user_name == username)).scalar()
        payments = db.session.execute(
            db.select(Fees).where(Fees.user_id == user.id and not Fees.already_paid)).scalars()
        for payment in payments:
            fee = db.get_or_404(Fees, payment.id)
            if (not fee.already_paid) and (datetime.datetime.now().strftime("%d-%m-%y") > fee.deadline):
                fee.amount = ((datetime.datetime.now() - datetime.datetime.strptime(fee.deadline,
                                                                                    "%d-%m-%y")).days) * 0.5
                db.session.commit()
            if fee.amount < 0:
                fee.amount = 0
                db.session.commit()
            payments_list.append(payment)
    else:
        return render_template("denied.html", msg="In order to do it, you need to be logged in!",
                               x=logged_in, u=username)
    return render_template("invoices.html", invoices_list=payments_list, x=logged_in, u=username)


@app.route('/invoice', methods=["GET", "POST"])
def invoice():
    global logged_in
    global username
    if logged_in:
        fee_id = int(request.args.get("id"))
        # print(fee_id)
        fee = db.get_or_404(Fees, fee_id)
        borrow_id = fee.borrow_id
        # print(borrow_id)
        the_borrowing = db.get_or_404(Borrowings, borrow_id)
        user_id = the_borrowing.user_id
        # print(user_id)
        the_user = db.get_or_404(Users, user_id)
        invoice_edi = edi(the_borrowing.id, the_borrowing.borrow_date, the_user.user_name, fee.amount)
        return render_template("denied.html", edimsg=invoice_edi, x=logged_in, u=username)
    return render_template("denied.html", msg="Something went wrong.", x=logged_in, u=username)


@app.route('/review', methods=["GET", "POST"])
def review():
    global logged_in
    global username
    if logged_in and request.method == "POST":
        # print(request.form["rating"])
        if "rating" in request.form:
            # print(request.form["rating"])
            product_id = request.form["id"]
            rating = Ratings(
                book_id=product_id,
                rating=int(request.form["rating"]),
                review=None,
                review_author=None
            )
            db.session.add(rating)
            db.session.commit()
            return render_template("index.html", msg="Successfully rated a book.")
        elif "review" in request.form:
            product_id = request.form["id"]
            rating = Ratings(
                book_id=product_id,
                rating=None,
                review=request.form["review"],
                review_author=username
            )
            db.session.add(rating)
            db.session.commit()
            return render_template("index.html", msg="Successfully added book review.")
        else:
            return render_template("denied.html", msg="Something went wrong during book rating.")
    average_rating = 0
    i = 0
    product_id = request.args.get('id')
    product_selected = db.get_or_404(Books, product_id)
    ratings = db.session.execute(db.select(Ratings).where(Ratings.book_id == product_id)).scalars()
    for current_rating in ratings:
        if current_rating.rating:  # to prevent from adding None to int
            average_rating += current_rating.rating
            i += 1
    if i:  # to prevent zero division
        average_rating = average_rating / i
    reviews_list = db.session.execute(db.select(Ratings).where(Ratings.book_id == product_id)).scalars()
    return render_template("review.html", product=product_selected, mean=average_rating,
                           reviews=reviews_list, x=logged_in, u=username)


def edi(borrow_number, borrow_date, user_name, amount_of_fee):
    sender = "LibraryID"
    recipient = "ClientID"
    control_reference = "ExampleReferenceNumber123"
    syntax_identifier = ("UNOC", 2)

    interchange = Interchange(
        sender=sender,
        recipient=recipient,
        control_reference=control_reference,
        syntax_identifier=syntax_identifier,
    )

    interchange.add_segment(Segment("UNA", [":", "+", ",", "?", " ", "'"]))

    interchange.add_segment(Segment("UNB", ["UNOC:2", f"{sender}",
                                            f"{recipient}", f"{datetime.datetime.now().strftime('%y%m%d:%H%M')}",
                                            f"{control_reference}"]))

    interchange.add_segment(Segment("UNG", ["Borrowing", "1", f"{sender}",
                                            f"{datetime.datetime.now().strftime('%y%m%d:%H%M')}",
                                            f"{control_reference}"]))

    interchange.add_segment(Segment("UNE", ["NumberOfSegments", "ReferenceNumber"]))

    interchange.add_segment(Segment("UNH", ["MessageReference", "Borrowing", "1", "ReaderOfEDIpython"]))

    interchange.add_segment(Segment("BGM", ["BORROWING", f"{borrow_number}"]))

    interchange.add_segment(Segment("DTM", ["Borrowing date", f"{borrow_date}"]))

    interchange.add_segment(Segment("NAD", ["Borrower", "User", f"{user_name}", ""]))

    interchange.add_segment(Segment("MOA", ["1", f"{amount_of_fee}", "$"]))

    interchange.add_segment(Segment("UNT", ["NumberOfSegments", "MessageReference"]))

    interchange.add_segment(Segment("UNZ", ["NumberOfGroups", "InterchangeReference"]))

    edifact = interchange.serialize()
    return edifact


@app.route('/logout')
def logout():
    global logged_in
    global username
    if logged_in:
        logged_in = False
        product_list = db.session.execute(db.select(Books)).scalars()
        return render_template("index.html", msg="Successfully logged out.",
                               products=product_list, x=logged_in, u=username)
    else:
        product_list = db.session.execute(db.select(Books)).scalars()
        return render_template("index.html", msg="You can't log out unlogged user.",
                               products=product_list, x=logged_in, u=username)


@app.route('/redirection')
def redirection():
    global logged_in
    global username
    if logged_in:
        fee_id = request.args.get('id')
        chosen_fee = db.get_or_404(Fees, fee_id)
        chosen_fee.already_paid = True
        db.session.commit()
        message = "Invoice has been paid."
        return render_template("denied.html", msg=message, x=logged_in, u=username)
    return render_template("denied.html", msg="Something went wrong.", x=logged_in, u=username)


if __name__ == "__main__":
    app.run(debug=True)
