import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# Make sure API key is set
API_KEY = "pk_629098af694e4b4da95b09ed466f5abb"


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
@login_required
def index():
    #check if user is logged first
    """Show portfolio of stocks"""
    stockinfo = db.execute("select stock, shares from owned_shares where user_id=?", session["user_id"])
    stocks =[]
    T = 0
    for stock in stockinfo:
        holder = lookup(stock['stock'])
        holder['shares'] = stock['shares']
        holder['total']  = holder['shares']*holder['price']
        stocks.append(holder)
        T = T+holder['total']
    T = round(T, 4)
    balance = db.execute("select cash from users where id=?", session['user_id'])
    balance = balance[0]['cash']
    T = balance+ T
    return render_template("index.html", stocks=stocks, balance=balance, T=T)

@app.route("/changepassword", methods=["GET", "POST"])
@login_required
def changepw():
    if request.method == "POST":
        password = request.form.get("password")
        print(password)
        print(f"hash of formed password is {generate_password_hash(password)}")
        pwhash = db.execute("select hash from users where id=?", session["user_id"])
        pwhash=pwhash[0]["hash"]
        print(f" hash from db is {pwhash}")
        if check_password_hash(pwhash, password):
            return redirect("/properchange")   
        else:
            return apology("password is wrong!")
    else:
        return render_template("change password.html")

@app.route("/properchange", methods=["GET", "POST"])
@login_required
def proper():
    if request.method=="POST":
        password=request.form.get("password")
        confirmation = request.form.get("confirmation")
        if password==confirmation:
            db.execute("update users set hash=? where id=?",generate_password_hash(password), session["user_id"])
            print(generate_password_hash(password))
            return render_template("changed.html")
            #don't forget to update db
        else:
            return apology("passwords do not match")
            
    else:
        return render_template("proper.html")


    

@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "POST":
        stock = request.form.get("symbol")
        shares = request.form.get("shares")
        stockbook = lookup(stock)
        #check that shares is an int
        if shares.isdigit():
            shares = int(shares)
            #check stock exists
            if stock and stockbook:
                #check shares is positive int
                if int(shares)>0:                    
                    #check user can afford stock 
                    balance = db.execute("select cash from users where id=?", session['user_id'])
                    balance = balance[0]['cash']
                    #check if balance is sufficient if not return apology
                    #if balance is sufficient update balance and insert transaction into database
                    total = stockbook['price']*shares 
                    if balance >= total:
                        balance = balance - total
                        db.execute("insert into transactions(user_id,stock_name,shares_number,price_at_trade,time,type) values(?,?,?,?,datetime(),'buy')", session['user_id'], stock, shares, stockbook['price'])
                        
                        #if user already owns this stock it should be an update statement istead of 
                        ownedstocks = db.execute("select stock from owned_shares where user_id=?", session["user_id"])
                        stocks =[]
                        for ownedstock in ownedstocks:
                            ownedstock = ownedstock["stock"]
                            stocks.append(ownedstock)
                        if stock in stocks:
                            #get number of already known shares
                            owned = db.execute("select shares from owned_shares where stock =? and user_id =?", stock, session["user_id"])
                            owned = owned[0]["shares"]
                            #update db
                            db.execute("update owned_shares set shares = ? where user_id =? and stock = ?", owned + shares, session["user_id"], stock)
                        else:
                            db.execute("insert into owned_shares(user_id, stock, shares) values(?,?,?)",session["user_id"], stock, shares)
                        #update balance value within db
                        db.execute("update users set cash=? where id=?",balance, session['user_id'])
                        return render_template("bought.html",balance=balance)
                    else:
                        return apology("Your balance is not sufficient")

                    return apology("all is well")
                else:
                    return apology("shares should be a positive integer")
            else:
                return apology("you either did not input a stock or stock does not exist")
        else:
            return apology("enter integer as number of shares")
    else:
        return render_template("buy.html")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    transactions = db.execute("select stock_name, shares_number, price_at_trade, time, type from transactions where user_id=?", session["user_id"])
    print(transactions)
    if len(transactions)==0:
        return render_template("history1.html")
    else:
        return render_template("history.html", transactions=transactions)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    #use lookup, get and post to get info about stocks
    """Get stock quote."""
    if request.method == "POST":
        symbol = request.form.get("quote")
        if symbol:
            val = lookup(symbol)
            return render_template("quoted.html", val=val)
        else:
            return apology("Enter symbol")
    else:
        return render_template("quote.html")
    #return apology("TODO")


@app.route("/register", methods=["GET", "POST"])
def register():
    #if get method is submitted show form and page, if post then add user given everything is well
    """Register user"""

    #register user via POST request
    if request.method == "POST":
        #verify input and register
        name = request.form.get("username")
        users = db.execute("select username from users")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")
        #return render_template("testing.html")
        #return apology("redirection works")
        
        #check if name exists, if not render an apology saying name does not exist
        if name:
            #check that username is not in use, else say it is in use
            print(users)
            if name not in users:
                if password==confirmation and password: #checking that password is not blank
                    db.execute("insert into users(username, hash) values(?,?)", name, generate_password_hash(password))
                    return redirect("/")
                else:
                    return apology("passwords do not match")
            else:
                return apology("Usernmae already exists")
        else:
            return apology("Enter username ") 
    
    #under get request display a form
    else:
        return render_template("register.html")
    #return apology("TODO")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    #implement post to actually sell and get to display page
    if request.method=="POST":
        #sell and update balance in account

        stock = request.form.get("stock")
        shares = request.form.get("shares")
        #check that form was sumbitted properly
        if stock and shares:
            
            
            #ensure shares is a postive int 
            if shares.isdigit():
                if int(shares)>=0:
                    shares = int(shares)

                    #get price of stock 
                    price = lookup(stock)["price"]

                    #number of shares user has and balance
                    ownedshares = db.execute("select shares from owned_shares where user_id=? and stock=?", session['user_id'], stock)
                    ownedshares = ownedshares[0]["shares"]
                    balance = db.execute("select cash from users where id=?",session['user_id'])
                    balance=balance[0]["cash"]
                    #make sure bro owns stocks
                    if ownedshares >= shares:
                        #calculate transaction value
                        value = shares*price
                        #increace balance
                        balance = balance + value
                        new = ownedshares - shares
                        #update transaction in db
                        db.execute("insert into transactions(user_id, stock_name, shares_number, price_at_trade, time, type) values(?,?,?,?,datetime(),'sell');", session["user_id"],stock,shares,price)
                        db.execute("update owned_shares set shares = ? where user_id=? and stock=?", new, session["user_id"],stock)
                        #update user balance in db
                        db.execute("update users set cash=? where id=?",balance, session['user_id'])

                        #logic to delete completely sold stocks from owned_shares
                        db.execute("delete from owned_shares where stock=? and user_id=? and shares=0", stock, session["user_id"])
                        """
                        #more complicated logic for the same purpose above that proved less efficient
                        book = db.execute("select stock, shares from owned_shares where user_id=?", session["user_id"])
                        print(f"this is the book {book}")
                        for item in book:
                            if item["shares"]==0:
                                db.execute("delete from owned_shares where user_id=? and stock")
                        """
                        return render_template("sold.html", balance=balance)
                        
                    else:
                        return apology("You don't have that many stocks")
                else:
                    return apology("shares should be positive")
            else:
                return apology("shares should be an integer")
        else:
            return apology("enter shares and stock")

    else:
        stocks = db.execute("select stock from owned_shares where user_id=?", session['user_id'])
        return render_template("sell.html", stocks=stocks)
    
