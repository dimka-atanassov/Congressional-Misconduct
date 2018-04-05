from flask import Flask, render_template, request, redirect
import pandas as pd
#import plotly.plotly as py
import plotly.graph_objs as go
import plotly.tools as tls
import yaml
import numpy as np
import sys
import logging
from logging.handlers import RotatingFileHandler
from plotly.graph_objs import Scatter, Figure, Layout, Bar
from plotly.offline import download_plotlyjs, init_notebook_mode, plot, iplot

app= Flask(__name__)
app.vars={}


@app.route('/')
def main():
    return redirect('/index')


def make_year(x):
    '''helper function that extracts a numeric year from
    different types of input'''
    if type(x)== int:
        return x
    elif type(x)==str:
        x = pd.Timestamp(x)
    return x.year

def load_data():
    '''read data from yaml file and load it into a dataframe'''
    try:
        with open('misconduct.yaml', 'r') as f:
            misconduct_json = yaml.load(f)
    except Exception as e:
        return render_template('/index.html', fig='Error loading data file')
        sys.exit(1)
    first_date=[]
    last_date =[]
    person=[]
    name=[]
    allegation=[]
    text=[] 
    tags = []
    all_tags = set()
    conseq_tags = []
    top_tags=set()


    for item in misconduct_json:
        allegation.append(item['allegation'])
        name.append(item['name'])
        person.append(item['person'])
        tags.append(item['tags'])
        text.append(item['text'])
        consequences = item['consequences']
        start_consequences = consequences[0]
        end_consequences = consequences[-1]
        curr_conseq_tags = []
        for conseq in consequences:
            if 'tags' in conseq.keys():
                curr_conseq_tags.extend(conseq['tags'].split(" "))
        conseq_tags.append(curr_conseq_tags)
        start_date = start_consequences['date']
        end_date = end_consequences['date']
        first_date.append(start_date)
        last_date.append(end_date)
        all_tags.update([x for x in item['tags'].split(" ")])
        all_tags.update([x for x in curr_conseq_tags])
        top_tags.update([x for x in item['tags'].split(" ")])


        
    misconduct_from_yaml = pd.DataFrame({'first_date': first_date,
                                         'last_date': last_date,
                                         'person':person,
                                         'name': name,
                                         'allegation': allegation,
                                         'text': text,
                                         'tags': tags,
                                         'conseq_tags': conseq_tags})

    for tag in all_tags:
        misconduct_from_yaml[tag] = np.zeros(len(last_date))
        misconduct_from_yaml[tag][misconduct_from_yaml['tags'].apply(lambda x: tag in x.split(" "))]=1
        misconduct_from_yaml[tag][misconduct_from_yaml['conseq_tags'].apply(lambda x: tag in x)]=1

    misconduct_from_yaml['first_year'] = misconduct_from_yaml['first_date'].apply(lambda x: make_year(x))
    misconduct_from_yaml['last_year'] = misconduct_from_yaml['last_date'].apply(lambda x: make_year(x))
    app.vars['misconduct'] = misconduct_from_yaml
    return misconduct_from_yaml


def create_plots(misconduct_by_year_total):
       
    corruption = Scatter(
    x=misconduct_by_year_total['first_year'],
    y= misconduct_by_year_total['corruption'],
    mode = 'lines+markers',
    name = 'Corruption')

    #app.logger.info(corruption)

    crime = Scatter(
    x=misconduct_by_year_total['first_year'],
    y= misconduct_by_year_total['crime'],
    mode = 'lines+markers',
    name = 'Crime')

    elections = Scatter(
    x=misconduct_by_year_total['first_year'],
    y= misconduct_by_year_total['elections'],
    mode = 'lines+markers',
    name = 'Elections')

    ethics = go.Scatter(
    x=misconduct_by_year_total['first_year'],
    y= misconduct_by_year_total['ethics'],
    mode = 'lines+markers',
    name='Ethics')

    sexual_harassment = Scatter(
    x=misconduct_by_year_total['first_year'],
    y= misconduct_by_year_total['sexual-harassment-abuse'],
    mode = 'lines+markers',
    name = 'Sexual Harassment')

    total = Scatter(
    x=misconduct_by_year_total['first_year'],
    y= misconduct_by_year_total['corruption']+ misconduct_by_year_total['crime']+ 
        misconduct_by_year_total['elections']+
        misconduct_by_year_total['ethics'] +
        misconduct_by_year_total['sexual-harassment-abuse'],
    mode = 'lines+markers',
    name = 'Total')


    layout = dict(title = 'Congressional Misconduct by Year',
              xaxis = dict(title = 'Year'),
              yaxis = dict(title = 'Number of Instances'),
              )
    
    fig = Figure(data=[corruption, crime, elections, ethics, sexual_harassment, total], layout=layout)

    plot_url = plot(fig, filename='line-mode', output_type='div')
    app.vars['by_year_plot'] = plot_url
    return plot_url
        
def create_bar(misconduct_by_year_total):

    layout = Layout(barmode='stack')

    corruption = Bar(
    x=misconduct_by_year_total['first_year'],
    y= misconduct_by_year_total['corruption'],
    name = 'Corruption')

    crime = Bar(
    x=misconduct_by_year_total['first_year'],
    y= misconduct_by_year_total['crime'],
    name = 'Crime')

    elections = Bar(
    x=misconduct_by_year_total['first_year'],
    y= misconduct_by_year_total['elections'],
    name = 'Elections')

    ethics = Bar(
    x=misconduct_by_year_total['first_year'],
    y= misconduct_by_year_total['ethics'],
    name='Ethics')

    sexual_harassment = Bar(
    x=misconduct_by_year_total['first_year'],
    y= misconduct_by_year_total['sexual-harassment-abuse'],
    name = 'Sexual Harassment')


    data=[corruption, crime, elections, ethics, sexual_harassment]
    fig = Figure(data=data, layout=layout)
    plot_url = plot(fig, filename='stacked-bar', output_type='div')

    app.vars['by_year_bar'] = plot_url
    return plot_url


@app.route('/index', methods=['GET', 'POST'])

def index():

    misconduct = {}
    load_data()
    
    if request.method == 'GET':
 
        if 'misconduct' in app.vars.keys():
            misconduct = app.vars['misconduct']
        else:
            return render_template('/index.html', fig='there was an error loading the data')

        if misconduct.shape[0]==0:
            return render_template('/index.html', fig='There was an error loading data')
        misconduct_by_year_total = misconduct.groupby('first_year')['corruption',
                                                                    'crime', 'elections', 'ethics',
                                                                    'sexual-harassment-abuse'].sum().reset_index()

        if misconduct_by_year_total.shape[0] ==0:
            return render_template('/index.html', fig='there was an error loading the data')
        else:
            fig = create_plots(misconduct_by_year_total)
            if fig:
                embeded_fig= fig
                return render_template('/index.html', fig=embeded_fig)
            else:
                return render_template('/index.html', fig='There was an error creating plots')

    ##post request            
    elif request.method =='POST':

        app.logger.info('in post')
        presentation_mode = request.form['options']
        if presentation_mode == 'StackBar':
            if 'by_year_bar' in app.vars.keys():
                fig = app.vars['by_year_bar']
                return render_template('/index.html', fig=fig)
            else:
                if 'misconduct' in app.vars.keys():
                    misconduct = app.vars['misconduct']
                    if misconduct.shape[0]==0:
                        return render_template('/index.html', fig='There was an error loading data')

                    misconduct_by_year_total = misconduct.groupby('first_year')['corruption',
                                                                    'crime', 'elections', 'ethics',
                                                                    'sexual-harassment-abuse'].sum().reset_index()

                    if misconduct_by_year_total.shape[0] ==0:
                        return render_template('/index.html', fig='there was an error loading the data')
                    
                    fig = create_bar(misconduct_by_year_total)
                    if fig:
                        return render_template('/index.html', fig=fig)
                    else:
                        return render_template('/index.html', fig='There was an error creating plots')
                        
        elif presentation_mode =='LinePlot':
            
            if 'by_year_plot' in app.vars.keys():
                fig = app.vars['by_year_plot']
                return render_template('/index.html', fig=fig)
            
            if 'misconduct' in app.vars.keys():
                misconduct = app.vars['misconduct']
                if misconduct.shape[0]==0:
                    return render_template('/index.html', fig='There was an error loading data')

                misconduct_by_year_total = misconduct.groupby('first_year')['corruption',
                                                            'crime', 'elections', 'ethics',
                                                            'sexual-harassment-abuse'].sum().reset_index()

                if misconduct_by_year_total.shape[0] ==0:
                    return render_template('/index.html', fig='there was an error loading the data')
                fig = create_plots(misconduct_by_year_total)
                if fig:
                    return render_template('/index.html', fig=fig)
                else:
                    return render_template('/index.html', fig='There was an error creating plots')
                
                        
if __name__ == '__main__':
    app.run(debug=True)
