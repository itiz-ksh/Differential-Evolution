"""Consistent interactive engineering plots."""
import plotly.graph_objects as go
from plotly.subplots import make_subplots

def response_plot(response):
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=.06, subplot_titles=('Motor speed', 'Controller voltage', 'Armature current'))
    for name, key, color, row in [('Reference','reference','#aab5cb',1),('Actual speed','speed','#45d4c0',1),('Voltage','voltage','#f7bd68',2),('Current','current','#8f9cff',3)]:
        fig.add_trace(go.Scatter(x=response['time'], y=response[key], name=name, line={'color':color, 'dash':'dash' if key=='reference' else 'solid'}), row=row,col=1)
    for row, label in enumerate(['Speed (RPM)','Voltage (V)','Current (A)'],1): fig.update_yaxes(title_text=label,row=row,col=1)
    fig.update_xaxes(title_text='Time (s)',row=3,col=1)
    return style(fig, 680)

def comparison_plot(original, optimized):
    fig=go.Figure()
    for name, y, color, dash in [('Reference',original['reference'],'#aab5cb','dash'),('Original PID',original['speed'],'#f7bd68','solid'),('Optimized PID',optimized['speed'],'#45d4c0','solid')]:
        fig.add_scatter(x=original['time'],y=y,name=name,line={'color':color,'dash':dash})
    fig.update_layout(title='Motor speed response comparison',xaxis_title='Time (s)',yaxis_title='Motor speed (RPM)')
    return style(fig)

def convergence_plot(history):
    fig=go.Figure(go.Scatter(x=list(range(1,len(history)+1)),y=history,mode='lines+markers',name='Best fitness',line={'color':'#45d4c0'}))
    fig.update_layout(title='Optimization convergence',xaxis_title='Generation',yaxis_title='Best objective value')
    return style(fig,350)

def style(fig, height=440):
    fig.update_layout(template='plotly_dark',paper_bgcolor='#111b2c',plot_bgcolor='#111b2c',height=height,margin=dict(l=20,r=20,t=55,b=20),legend=dict(orientation='h',y=1.08))
    fig.update_xaxes(showgrid=True,gridcolor='#29374b'); fig.update_yaxes(showgrid=True,gridcolor='#29374b')
    return fig
