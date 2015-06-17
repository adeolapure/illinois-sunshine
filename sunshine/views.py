from flask import Blueprint, render_template, abort, request, make_response
from sunshine.database import db_session
from sunshine.models import Candidate, Committee, Receipt, FiledDoc
import sqlalchemy as sa
import json
from datetime import datetime, timedelta

views = Blueprint('views', __name__)

@views.route('/')
def index():
    two_days_ago = datetime.now() - timedelta(days=3)
    
    recent_donations = db_session.query(Receipt)\
                                 .join(FiledDoc)\
                                 .filter(Receipt.received_date >= two_days_ago)\
                                 .order_by(FiledDoc.received_datetime.desc())\
                                 .limit(10)
    
    top_ten = ''' 
        SELECT * FROM candidate_money LIMIT 5;
    '''
    
    engine = db_session.bind
    top_ten = engine.execute(sa.text(top_ten))

    return render_template('index.html', 
                           recent_donations=recent_donations,
                           top_ten=top_ten)

@views.route('/recent-contributions')
def recent_contributions():
    seven_days_ago = datetime.now() - timedelta(days=8)
    
    recent_donations = db_session.query(Receipt)\
                                 .join(FiledDoc)\
                                 .filter(Receipt.received_date >= seven_days_ago)\
                                 .order_by(FiledDoc.received_datetime.desc())

    return render_template('recent-contributions.html', 
                           recent_donations=recent_donations)

@views.route('/about/')
def about():
    return render_template('about.html')

@views.route('/candidates/')
def candidates():
    money = '''
        SELECT * FROM candidate_money LIMIT 10
    '''
    engine = db_session.bind
    rows = engine.execute(sa.text(money))
    return render_template('candidates.html', rows=rows)

@views.route('/search/')
def search():
    return render_template('search.html')

@views.route('/candidate/<candidate_id>/')
def candidate(candidate_id):
    try:
        candidate_id = int(candidate_id)
    except ValueError:
        return abort(404)
    candidate = db_session.query(Candidate).get(candidate_id)
    if not candidate:
        return abort(404)
    return render_template('candidate-detail.html', candidate=candidate)

@views.route('/committees/')
def committees():
    return render_template('committees.html')

@views.route('/committee/<committee_id>/')
def committee(committee_id):
    try:
        committee_id = int(committee_id)
    except ValueError:
        return abort(404)
    committee = db_session.query(Committee).get(committee_id)
    
    if not committee:
        return abort(404)
    
    engine = db_session.bind
    
    latest_filing = ''' 
        SELECT * FROM most_recent_filings
        WHERE committee_id = :committee_id
        ORDER BY received_datetime
        LIMIT 1
    '''

    latest_filing = engine.execute(sa.text(latest_filing), 
                                   committee_id=committee_id).first()
    
    params = {'committee_id': committee_id}

    if latest_filing:

        recent_receipts = ''' 
            SELECT 
              receipts.id,
              receipts.amount,
              receipts.first_name,
              receipts.last_name,
              filed.doc_name,
              filed.received_datetime
            FROM receipts
            JOIN filed_docs AS filed
              ON receipts.filed_doc_id = filed.id
            WHERE receipts.committee_id = :committee_id
              AND receipts.received_date > :end_date
            ORDER BY receipts.received_date DESC
        '''
        controlled_amount = latest_filing.end_funds_available
        params['end_date'] = latest_filing.reporting_period_end

    else:

        recent_receipts = ''' 
            SELECT 
              receipts.id,
              receipts.amount,
              receipts.first_name,
              receipts.last_name,
              filed.doc_name,
              filed.received_datetime
            FROM receipts
            JOIN filed_docs AS filed
              ON receipts.filed_doc_id = filed.id
            WHERE receipts.committee_id = :committee_id
            ORDER BY receipts.received_date DESC
        '''
        
        controlled_amount = 0

    recent_receipts = list(engine.execute(sa.text(recent_receipts),**params))
        
    recent_total = 0

    if recent_receipts:
        recent_total = sum([r.amount for r in recent_receipts])
        controlled_amount += recent_total

    return render_template('committee-detail.html', 
                           committee=committee, 
                           recent_receipts=recent_receipts,
                           recent_total=recent_total,
                           latest_filing=latest_filing,
                           controlled_amount=controlled_amount)

@views.route('/contributions/')
def contributions():
    contributions = db_session.query(Receipt)\
                        .order_by(Receipt.received_date.desc())\
                        .limit(100)
    return render_template('contributions.html', contributions=contributions)

@views.route('/contribution/<receipt_id>/')
def contribution(receipt_id):
    try:
        receipt_id = int(receipt_id)
    except ValueError:
        return abort(404)
    receipt = db_session.query(Receipt).get(receipt_id)
    if not receipt:
        return abort(404)
    return render_template('contribution-detail.html', receipt=receipt)
