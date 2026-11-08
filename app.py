"""Interactive Streamlit front end for DC motor PID tuning."""
from pathlib import Path
import streamlit as st
from modules.dc_motor import Motor, simulate
from modules.pid_controller import PID
from modules.performance_metrics import calculate_metrics
from modules.differential_evolution import optimize
from modules.visualization import response_plot, comparison_plot, convergence_plot
from modules.report_generator import csv_bytes, pdf_bytes, fmt
from utils.validation import validate_simulation

st.set_page_config(page_title='PID Tuning Lab', page_icon='⚙️', layout='wide')
st.markdown('<style>'+Path('assets/custom.css').read_text()+'</style>',unsafe_allow_html=True)
for key,value in {'motor':Motor(), 'pid':PID(), 'reference':1000., 'duration':5., 'manual':None, 'optimization':None}.items():
    if key not in st.session_state: st.session_state[key]=value
s=st.session_state
pages=['Dashboard','Motor Configuration','Manual PID Tuning','Automatic Optimization','Performance Comparison','Reports and Export','About Project']
st.sidebar.markdown('<p class="eyebrow">CONTROL SYSTEMS LAB</p>',unsafe_allow_html=True)
st.sidebar.title('PID Tuning')
page=st.sidebar.radio('Navigate', pages, label_visibility='collapsed')
st.sidebar.caption('DC motor  ·  Differential Evolution')

def heading(kicker,title,description):
    st.markdown(f'<p class="eyebrow">{kicker}</p>',unsafe_allow_html=True); st.title(title); st.markdown(f'<p class="subtitle">{description}</p>',unsafe_allow_html=True)

def metrics(response, reference):
    m=calculate_metrics(response['time'],response['speed'],reference)
    cols=st.columns(5)
    for c,label,key,unit in zip(cols,['Rise time','Settling time','Overshoot','Final error','IAE'],['rise_time','settling_time','overshoot','steady_state_error','iae'],['s','s','%','RPM','RPM s']): c.metric(label, f'{fmt(m[key])} {unit}' if m[key] is not None else 'Not reached')
    if reference > 0 and max(response['speed']) < .9*reference: st.warning('The response did not reach 90% of the reference during the simulation.')
    if reference > 0 and m['settling_time'] is None: st.warning('The response did not settle within the 2% band during the simulation.')
    return m

def current_pair():
    if s.optimization is None: raise ValueError('Run automatic optimization before comparing or exporting a report.')
    opt=s.optimization
    if opt['conditions'] != (s.motor,s.reference,s.duration): raise ValueError('Motor settings, reference or duration changed since optimization. Run optimization again for a valid comparison.')
    a=simulate(s.motor,s.pid,s.reference,s.duration); b=simulate(s.motor,opt['result'].pid,s.reference,s.duration)
    return a,b,opt['result']

def comparison_table(a,b,opt):
    ma=calculate_metrics(a['time'],a['speed'],s.reference); mb=calculate_metrics(b['time'],b['speed'],s.reference)
    rows=[]
    for label,x,y in [('Kp',s.pid.kp,opt.pid.kp),('Ki',s.pid.ki,opt.pid.ki),('Kd',s.pid.kd,opt.pid.kd),('Rise time (s)',ma['rise_time'],mb['rise_time']),('Settling time (s)',ma['settling_time'],mb['settling_time']),('Overshoot (%)',ma['overshoot'],mb['overshoot']),('Final error (RPM)',ma['steady_state_error'],mb['steady_state_error']),('IAE (RPM s)',ma['iae'],mb['iae'])]:
        xx=abs(x) if x is not None else None; yy=abs(y) if y is not None else None
        improvement=f'{100*(xx-yy)/xx:.1f}%' if label not in ('Kp','Ki','Kd') and xx is not None and yy is not None and xx > 1e-12 else '—'
        rows.append({'Metric':label,'Original PID':fmt(x),'Optimized PID':fmt(y),'Improvement':improvement})
    st.dataframe(rows,hide_index=True,use_container_width=True)
    st.caption('Improvement is the reduction in each metric; for signed final error it uses absolute magnitude. Negative values indicate a worse result.')

if page=='Dashboard':
    heading('Engineering dashboard','PID Controller Tuning','Explore a simulated DC motor and tune its controller using Differential Evolution.')
    cols=st.columns(4); cols[0].metric('Target speed',f'{s.reference:g} RPM'); cols[1].metric('Simulation horizon',f'{s.duration:g} s'); cols[2].metric('Voltage limit',f'{s.motor.max_voltage:g} V'); cols[3].metric('Optimization', 'Completed' if s.optimization else 'Not run')
    st.divider(); left,right=st.columns(2)
    with left:
        st.subheader('Motor configuration'); st.json(vars(s.motor),expanded=True)
    with right:
        st.subheader('Current manual controller'); st.json(vars(s.pid),expanded=True)
        if s.optimization: st.info('Last run: '+s.optimization['result'].message)
        else: st.info('No optimization has been run in this session.')
    st.markdown('**Get started**  ·  Configure the motor, run a manual response, then optimize and compare using the sidebar.')
elif page=='Motor Configuration':
    heading('Plant settings','Motor Configuration','Set the electrical and mechanical parameters of the armature-controlled motor.')
    m=s.motor
    with st.form('motor_form'):
        a,b=st.columns(2)
        with a:
            R=st.number_input('Resistance R (Ω)',value=m.resistance,format='%.6f'); L=st.number_input('Inductance L (H)',value=m.inductance,format='%.6f'); Kt=st.number_input('Torque constant Kt (N m/A)',value=m.torque_constant,format='%.6f'); Ke=st.number_input('Back EMF constant Ke (V s/rad)',value=m.back_emf,format='%.6f')
        with b:
            J=st.number_input('Inertia J (kg m²)',value=m.inertia,format='%.6f'); friction=st.number_input('Viscous friction b (N m s/rad)',value=m.friction,format='%.6f'); vmax=st.number_input('Maximum voltage (V)',value=m.max_voltage,format='%.4f'); load=st.number_input('Load torque TL (N m)',value=m.load_torque,format='%.6f')
        if st.form_submit_button('Save motor configuration'):
            try:
                candidate=Motor(R,L,Kt,Ke,J,friction,vmax,load); validate_simulation(candidate,s.pid,s.reference,s.duration); s.motor=candidate; st.success('Motor configuration saved.')
            except ValueError as e: st.error(str(e))
    st.latex(r'L\dot{i}=V-Ri-K_e\omega\qquad J\dot{\omega}=K_t i-b\omega-T_L')
elif page=='Manual PID Tuning':
    heading('Closed-loop simulation','Manual PID Tuning','Adjust controller gains and observe the motor response, voltage, and armature current.')
    with st.form('manual_form'):
        cols=st.columns(5)
        kp=cols[0].number_input('Kp',value=s.pid.kp,format='%.4f'); ki=cols[1].number_input('Ki',value=s.pid.ki,format='%.4f'); kd=cols[2].number_input('Kd',value=s.pid.kd,format='%.4f'); ref=cols[3].number_input('Desired speed (RPM)',value=s.reference,format='%.2f'); duration=cols[4].number_input('Duration (s)',value=s.duration,format='%.2f')
        if st.form_submit_button('Run Manual Simulation'):
            try:
                pid=PID(kp,ki,kd); result=simulate(s.motor,pid,ref,duration); s.pid=pid; s.reference=ref; s.duration=duration; s.manual={'response':result,'conditions':(s.motor,pid,ref,duration)}; st.success('Simulation complete.')
            except (ValueError,ArithmeticError,RuntimeError) as e: st.error(f'Simulation could not run: {e}')
    if s.manual:
        if s.manual['conditions'] != (s.motor,s.pid,s.reference,s.duration): st.warning('Showing the previous simulation; run again to apply current settings.')
        response=s.manual['response']; metrics(response,float(response['reference'][0])); st.plotly_chart(response_plot(response),use_container_width=True)
elif page=='Automatic Optimization':
    heading('Evolutionary search','Automatic PID Optimization','Minimize a weighted objective over the selected gain bounds.')
    st.caption(f'Current conditions: {s.reference:g} RPM · {s.duration:g} s · {s.motor.max_voltage:g} V limit. Set speed and duration in Manual PID Tuning.')
    with st.form('opt_form'):
        cols=st.columns(3); bounds=[]
        for c,name,upper in zip(cols,['Kp','Ki','Kd'],[1.,3.,.1]):
            with c:
                st.markdown(f'**{name} bounds**'); lo=st.number_input(f'{name} lower',value=0.,format='%.4f'); hi=st.number_input(f'{name} upper',value=upper,format='%.4f'); bounds.append((lo,hi))
        cols=st.columns(5)
        pop=cols[0].number_input('Population multiplier',min_value=1,value=6,step=1); gen=cols[1].number_input('Max generations',min_value=1,value=12,step=1); mutation=cols[2].number_input('Mutation factor',value=.7,format='%.2f'); cross=cols[3].number_input('Crossover probability',value=.7,format='%.2f'); seed=cols[4].number_input('Random seed',min_value=0,value=42,step=1)
        submitted=st.form_submit_button('Optimize PID Parameters')
    if submitted:
        try:
            bar=st.progress(0,text='Initializing population…')
            def progress(n,total,value): bar.progress(min(n/total,1.),text=f'Generation {n}/{total} · best objective {value:.4f}')
            with st.spinner('Simulating candidate controllers…'):
                result=optimize(s.motor,s.reference,s.duration,bounds,int(pop),int(gen),mutation,cross,int(seed),progress)
            s.optimization={'result':result,'conditions':(s.motor,s.reference,s.duration)}; bar.empty(); st.success('Optimization finished.')
        except (ValueError,ArithmeticError,RuntimeError) as e: st.error(f'Optimization could not run: {e}')
    if s.optimization:
        opt=s.optimization['result']; cols=st.columns(5)
        for c,label,val in zip(cols,['Kp','Ki','Kd','Best objective','Generations'],[opt.pid.kp,opt.pid.ki,opt.pid.kd,opt.fitness,opt.generations]): c.metric(label,fmt(val))
        st.write(f'**Status:** {opt.message}  ·  **Converged:** {opt.success}  ·  **Elapsed:** {opt.seconds:.2f} s')
        if s.optimization['conditions'] != (s.motor,s.reference,s.duration): st.warning('This result used previous simulation conditions; rerun optimization before comparing.')
        st.plotly_chart(convergence_plot(opt.history),use_container_width=True)
    with st.expander('Objective and algorithm details'):
        st.write('SciPy Differential Evolution uses mutation, crossover and selection. Fitness = normalized IAE + 2 × overshoot fraction + normalized settling time + 2 × absolute normalized final error. A response that never settles receives a settling penalty of 2; invalid responses receive 1,000,000. IAE is normalized by reference and duration. A 1 RPM scale is used at zero reference.')
elif page=='Performance Comparison':
    heading('Side-by-side analysis','Performance Comparison','Both controllers run on the same current motor and simulation settings.')
    try:
        a,b,opt=current_pair(); st.plotly_chart(comparison_plot(a,b),use_container_width=True); comparison_table(a,b,opt)
    except (ValueError,ArithmeticError,RuntimeError) as e: st.info(str(e))
elif page=='Reports and Export':
    heading('Results package','Reports and Export','Download recorded simulation data and an engineering report.')
    if s.manual:
        try: st.download_button('Download manual simulation CSV',csv_bytes(s.manual['response']),'manual_response.csv','text/csv')
        except (ValueError, OSError) as e: st.error(f'CSV generation failed: {e}')
    else: st.info('Run a manual simulation to export its recorded data.')
    try:
        a,b,opt=current_pair()
        st.download_button('Download optimized simulation CSV',csv_bytes(b),'optimized_response.csv','text/csv')
        st.download_button('Download PDF report',pdf_bytes(s.motor,s.pid,opt,a,b,s.reference,s.duration),'pid_tuning_report.pdf','application/pdf')
        st.caption('The report uses the current manual gains and the optimization run under the same motor conditions.')
    except (ValueError,ArithmeticError,RuntimeError,OSError) as e: st.info(str(e))
else:
    heading('Project notes','About Project','A practical demonstration of closed-loop control and evolutionary optimization.')
    st.markdown('''The armature current and angular velocity are integrated from the motor equations. The PID uses error in rad/s, a filtered derivative on measurement, voltage saturation, and back-calculation anti-windup. Differential Evolution searches bounded non-negative gains; the reported optimum is the best found within the configured search budget.

**Metric conventions:** Rise time is between the first sampled 10% and 90% crossings. Settling time is the first sample after the last sample outside the 2% band; it is not confirmed if the final sample is outside. Overshoot is clamped at zero. Final error is signed reference minus final speed; IAE uses trapezoidal integration in RPM seconds. Relative metrics are undefined at zero reference. A finite simulation cannot prove future settling.

**Model limitations:** idealized linear motor, constant load, continuous controller, fixed derivative filter and no sensor noise, thermal limits or actuator dynamics.''')
