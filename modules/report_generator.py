"""CSV and multi-page PDF reports from actual simulation results."""
import csv, io
from datetime import datetime
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from modules.performance_metrics import calculate_metrics

def csv_bytes(response):
    out=io.StringIO(newline=''); writer=csv.writer(out)
    writer.writerow(['time_s','reference_rpm','speed_rpm','current_A','voltage_V','error_rpm'])
    writer.writerows(zip(*(response[k] for k in ('time','reference','speed','current','voltage','error'))))
    return out.getvalue().encode('utf-8')

def fmt(value):
    return 'Not reached' if value is None else f'{value:.4g}'

def pdf_bytes(motor, original_pid, opt, original, optimized, reference, duration):
    buf=io.BytesIO(); m1=calculate_metrics(original['time'],original['speed'],reference); m2=calculate_metrics(optimized['time'],optimized['speed'],reference)
    with PdfPages(buf) as pdf:
        fig=plt.figure(figsize=(8.27,11.69)); fig.text(.08,.95,'PID CONTROLLER TUNING',fontsize=21,weight='bold',color='#19334c'); fig.text(.08,.915,'DC motor  /  Differential Evolution',fontsize=12)
        fig.text(.08,.88,datetime.now().astimezone().strftime('Generated %Y-%m-%d %H:%M %Z'),fontsize=9,color='gray')
        config='\n'.join(f'{k.replace("_"," ").title()}: {v:.5g}' for k,v in vars(motor).items())
        fig.text(.08,.82,'MOTOR CONFIGURATION',fontsize=12,weight='bold'); fig.text(.08,.79,config+f'\nReference: {reference:g} RPM\nDuration: {duration:g} s',va='top',fontsize=10,linespacing=1.5)
        fig.text(.55,.82,'CONTROLLER GAINS',fontsize=12,weight='bold'); fig.text(.55,.79,'Original\n'+ '\n'.join(f'{k}: {v:.5g}' for k,v in vars(original_pid).items())+'\n\nOptimized\n'+'\n'.join(f'{k}: {v:.5g}' for k,v in vars(opt.pid).items()),va='top',fontsize=10,linespacing=1.5)
        rows=[[label,fmt(m1[k]),fmt(m2[k])] for label,k in [('Rise time (s)','rise_time'),('Settling time (s)','settling_time'),('Overshoot (%)','overshoot'),('Final error (RPM)','steady_state_error'),('IAE (RPM s)','iae')]]
        ax=fig.add_axes([.08,.25,.84,.22]); ax.axis('off'); ax.table(cellText=rows,colLabels=['Metric','Original','Optimized'],loc='center',cellLoc='center').scale(1,1.7)
        fig.text(.08,.18,f'Best objective: {opt.fitness:.5g}  |  Generations: {opt.generations}  |  Success: {opt.success}',fontsize=10)
        fig.text(.08,.14, f"Analysis: IAE changed from {fmt(m1['iae'])} to {fmt(m2['iae'])} RPM s; overshoot changed from {fmt(m1['overshoot'])}% to {fmt(m2['overshoot'])}%.", fontsize=9, wrap=True)
        fig.text(.08,.11,'Final error is signed; settling requires the response to remain within 2% through the simulation end.',fontsize=8,wrap=True)
        pdf.savefig(fig); plt.close(fig)
        fig, axes=plt.subplots(2,1,figsize=(8.27,11.69),layout='constrained')
        axes[0].plot(original['time'], original['reference'],'--',label='Reference'); axes[0].plot(original['time'],original['speed'],label='Original'); axes[0].plot(optimized['time'],optimized['speed'],label='Optimized'); axes[0].set(title='Motor response comparison',xlabel='Time (s)',ylabel='Speed (RPM)'); axes[0].legend(); axes[0].grid(alpha=.3)
        axes[1].plot(range(1,len(opt.history)+1),opt.history,marker='o'); axes[1].set(title='Optimization convergence',xlabel='Generation',ylabel='Best objective'); axes[1].grid(alpha=.3)
        fig.suptitle('Simulation results and optimization history',fontsize=16); pdf.savefig(fig); plt.close(fig)
    return buf.getvalue()
