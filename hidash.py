"""
 * Copyright (C) [2026] [Erik Whitfield]
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program. If not, see <https://www.gnu.org/licenses/>.
"""
import os
import pandas as pd
import streamlit as st
import plotly.express as px
from google.oauth2 import service_account
from googleapiclient.discovery import build
from anthropic import Anthropic

# Page config
st.set_page_config(page_title="PADI Analytics", layout="wide")

# Constants
SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
STUDENT_SHEET_ID = "12eUyUTZti7_1TzcGXZumY_ZvIRa9U1wXBESAdos-ODo"
TEACHER_SHEET_ID = "1G24hVKlg-8TdYUb655z16bURreQZWByPNPurwidYFdE"

USERS = {
    "admin": os.getenv("ADMIN_PASSWORD", "admin123"),
    "ancheta": os.getenv("PASSWORD_ANCHETA", "teacher123"),
    "haskell": os.getenv("PASSWORD_HASKELL", "teacher123"),
    "walker": os.getenv("PASSWORD_WALKER", "teacher123"),
    "thielk": os.getenv("PASSWORD_THIELK", "teacher123"),
    "kagawa": os.getenv("PASSWORD_KAGAWA", "teacher123"),
    "hashimoto": os.getenv("PASSWORD_HASHIMOTO", "teacher123"),
    "jerome": os.getenv("PASSWORD_JEROME", "teacher123"),
    "ramos": os.getenv("PASSWORD_RAMOS", "teacher123"),
}

# Initialize session state
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# Login check
if not st.session_state.logged_in:
    # Center login form
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.title("🔐 PADI Analytics Login")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        
        if st.button("Login", use_container_width=True):
            if username in USERS and USERS[username] == password:
                st.session_state.logged_in = True
                st.session_state.username = username
                st.rerun()
            else:
                st.error("Invalid credentials")
    st.stop()

# Load Google Sheets data
# Check for base64 encoded credentials in environment variable (for Railway)
creds_b64 = os.getenv('GOOGLE_CREDENTIALS_BASE64')

if creds_b64:
    # Decode from base64
    import base64
    import json
    creds_json = base64.b64decode(creds_b64)
    creds_dict = json.loads(creds_json)
    creds = service_account.Credentials.from_service_account_info(
        creds_dict, scopes=SCOPES
    )
else:
    # Use local credentials.json file
    creds = service_account.Credentials.from_service_account_file(
        "credentials.json",
        scopes=SCOPES
    )

service = build("sheets", "v4", credentials=creds)

# Load student data
result = service.spreadsheets().values().get(
    spreadsheetId=STUDENT_SHEET_ID,
    range="Form Responses 1!A2:M"
).execute()
values = result.get("values", [])

student_df = pd.DataFrame(values, columns=[
    "Timestamp", "TeacherLastName", "Grade", "Task", 
    "LikedPartner", "DislikePartnerReason", "Choice", "ShowLearning",
    "Engaged", "Confused", "Prepared", "LikedText", "DislikedText"
])

# Parse timestamp
student_df["Timestamp"] = pd.to_datetime(student_df["Timestamp"], format="%m/%d/%Y %H:%M:%S", errors="coerce")

# Filter to only include teachers in USERS list (exclude non-official teachers)
valid_teachers = [username for username in USERS.keys() if username != "admin"]
student_df = student_df[
    student_df["TeacherLastName"].str.lower().str.strip().isin(valid_teachers)
]

# Load teacher reflections
result = service.spreadsheets().values().get(
    spreadsheetId=TEACHER_SHEET_ID,
    range="Form Responses 1!A2:K"
).execute()
values = result.get("values", [])

teacher_df = pd.DataFrame(values, columns=[
    "Timestamp", "Email", "FullName", "GradeLevel", "TaskType",
    "WentWell", "Struggled", "Concerns", "Revisions", "Principles", "Other"
])
teacher_df["Timestamp"] = pd.to_datetime(teacher_df["Timestamp"], format="%m/%d/%Y %H:%M:%S", errors="coerce")

# Filter to only include teachers in USERS list
valid_teachers = [username for username in USERS.keys() if username != "admin"]
# Match against last names in FullName (case insensitive)
teacher_df = teacher_df[
    teacher_df["FullName"].str.lower().str.split().str[-1].isin(valid_teachers)
]

# Compact header with filters
if st.session_state.username == "admin":
    # Admin view - show teacher filter
    col1, col2, col3, col4 = st.columns([2, 1.5, 1.5, 1])
    with col1:
        st.markdown("### PADI Analytics")
    with col2:
        start_date = st.date_input("From", value=student_df["Timestamp"].min(), label_visibility="collapsed")
    with col3:
        end_date = st.date_input("To", value=student_df["Timestamp"].max(), label_visibility="collapsed")
    with col4:
        # Get list of teachers from data
        teacher_list = ["Select a teacher..."] + sorted(student_df["TeacherLastName"].str.lower().str.strip().unique().tolist())
        teacher_filter = st.selectbox(
            "Teacher",
            teacher_list,
            label_visibility="collapsed"
        )
    with col4:
        if st.button("Logout"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
else:
    # Teacher view - no teacher filter
    col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
    with col1:
        st.markdown("### PADI Analytics")
    with col2:
        start_date = st.date_input("From", value=student_df["Timestamp"].min(), label_visibility="collapsed")
    with col3:
        end_date = st.date_input("To", value=student_df["Timestamp"].max(), label_visibility="collapsed")
    with col4:
        if st.button("Logout"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
    teacher_filter = None  # Teachers don't get to filter by teacher

# Dark gray color scheme (no black)
bg_color = "#2b2b2b"
text_color = "#e0e0e0"
plot_bg = "#3a3a3a"
grid_color = "#555555"

st.markdown(f"""
    <style>
    .stApp {{
        background-color: {bg_color};
        color: {text_color};
    }}
    .stMarkdown, .stText {{
        color: {text_color};
    }}
    </style>
""", unsafe_allow_html=True)

# Filter data by date range
filtered_df = student_df[
    (student_df["Timestamp"] >= pd.to_datetime(start_date)) & 
    (student_df["Timestamp"] <= pd.to_datetime(end_date))
]

# Filter by teacher
if st.session_state.username == "admin":
    # Admin can filter by specific teacher or see aggregated data
    if teacher_filter == "Select a teacher...":
        # Show aggregated data for all teachers - no filtering
        pass
    else:
        # Filter to specific teacher
        filtered_df = filtered_df[
            filtered_df["TeacherLastName"].str.lower().str.strip() == teacher_filter.lower()
        ]
else:
    # Regular teachers only see their own data
    filtered_df = filtered_df[
        filtered_df["TeacherLastName"].str.lower().str.strip() == st.session_state.username.lower()
    ]

# Two column layout - main dashboard (70%) and AI chat (30%)
col_main, col_chat = st.columns([7, 3])

with col_main:
    # Compact metric cards
    total = len(filtered_df)
    
    if total > 0:
        engaged_pct = (filtered_df["Engaged"] == "Yes").sum() / total * 100
        confused_pct = (filtered_df["Confused"] == "Yes").sum() / total * 100
        choice_pct = (filtered_df["Choice"] == "Yes").sum() / total * 100
        prepared_pct = (filtered_df["Prepared"] == "Yes").sum() / total * 100
        partner_pct = (filtered_df["LikedPartner"] == "Yes").sum() / total * 100
    else:
        engaged_pct = confused_pct = choice_pct = prepared_pct = partner_pct = 0
    
    m1, m2, m3, m4, m5, m6 = st.columns(6)
    m1.metric("Engaged", f"{engaged_pct:.0f}%")
    m2.metric("Confused", f"{confused_pct:.0f}%")
    m3.metric("Choice", f"{choice_pct:.0f}%")
    m4.metric("Prepared", f"{prepared_pct:.0f}%")
    m5.metric("Liked Partner", f"{partner_pct:.0f}%")
    m6.metric("Total Responses", f"{total}")
    
    # Trend chart by task cycle/instance - always show all tasks
    if total > 0:
        st.write("**Trends Over Time**")
        
        # Check if we're in admin view with all teachers (no instance detection for aggregated view)
        is_aggregated_view = (st.session_state.username == "admin" and teacher_filter == "Select a teacher...")
        
        if is_aggregated_view:
            # For aggregated admin view, just show simple task breakdown without instances
            weekly_data = []
            
            for task_type in ["Instructional Task #1", "Instructional Task #2", "End-of-Unit Performance Task"]:
                task_df = filtered_df[filtered_df['Task'] == task_type]
                
                if len(task_df) > 0:
                    task_label = task_type.replace("Instructional Task #", "T").replace("End-of-Unit Performance Task", "End")
                    
                    for metric in ["Engaged", "Confused", "Choice", "Prepared"]:
                        yes_count = (task_df[metric] == "Yes").sum()
                        total_count = len(task_df)
                        pct = yes_count / total_count * 100 if total_count > 0 else 0
                        
                        weekly_data.append({
                            'Instance': task_label,
                            'Metric': metric,
                            'Percentage': pct,
                            'Count': f"({yes_count}/{total_count})"
                        })
        else:
            # For single teacher view, detect instances
            # Sort by timestamp to get chronological order
            sorted_df = filtered_df.sort_values('Timestamp').copy()
            
            # Robust cycle detection: time gaps + End Unit markers
            # For each task, find instances separated by >14 day gap AND an End Unit in between
            
            def assign_instances(df):
                """Assign instance numbers to tasks based on time gaps and End Unit markers"""
                df = df.copy()
                df['Instance'] = 1
                
                for task_type in ["Instructional Task #1", "Instructional Task #2", "End-of-Unit Performance Task"]:
                    task_mask = df['Task'] == task_type
                    task_dates = df[task_mask]['Timestamp'].sort_values()
                    
                    if len(task_dates) == 0:
                        continue
                    
                    instance_num = 1
                    last_date = None
                    
                    for idx in task_dates.index:
                        current_date = df.loc[idx, 'Timestamp']
                        
                        if last_date is not None:
                            # Check for time gap (>14 days)
                            time_gap = (current_date - last_date).days > 14
                            
                            # Check if End Unit occurred between last_date and current_date
                            end_unit_between = (
                                (df['Task'] == "End-of-Unit Performance Task") &
                                (df['Timestamp'] > last_date) &
                                (df['Timestamp'] < current_date)
                            ).any()
                            
                            # New instance if BOTH conditions met
                            if time_gap and end_unit_between:
                                instance_num += 1
                        
                        df.loc[idx, 'Instance'] = instance_num
                        last_date = current_date
                
                return df
            
            sorted_df = assign_instances(sorted_df)
            
            # Show all instances for all tasks
            weekly_data = []
            
            for task_type in ["Instructional Task #1", "Instructional Task #2", "End-of-Unit Performance Task"]:
                task_df = sorted_df[sorted_df['Task'] == task_type]
                unique_instances = task_df.groupby('Instance')
                
                task_label = task_type.replace("Instructional Task #", "T").replace("End-of-Unit Performance Task", "End")
                
                for instance_num, instance_data in unique_instances:
                    for metric in ["Engaged", "Confused", "Choice", "Prepared"]:
                        yes_count = (instance_data[metric] == "Yes").sum()
                        total_count = len(instance_data)
                        pct = yes_count / total_count * 100 if total_count > 0 else 0
                        
                        # Only show instance number if > 1
                        if task_df['Instance'].max() > 1:
                            label = f"{task_label} I{int(instance_num)}"
                        else:
                            label = task_label
                        
                        weekly_data.append({
                            'Instance': label,
                            'Metric': metric,
                            'Percentage': pct,
                            'Count': f"({yes_count}/{total_count})"
                        })
        
        if len(weekly_data) > 0:
            weekly_melted = pd.DataFrame(weekly_data)
            
            # Create bar chart instead of line chart for discrete instances
            fig = px.bar(
                weekly_melted,
                x='Instance',
                y='Percentage',
                color='Metric',
                barmode='group',
                range_y=[0, 100],
                custom_data=['Count'],
                color_discrete_map={
                    'Engaged': '#ffffff',
                    'Confused': '#cccccc', 
                    'Choice': '#999999',
                    'Prepared': '#666666'
                }
            )
            
            # Update hover template
            fig.update_traces(
                hovertemplate='<b>%{fullData.name}</b><br>%{y:.0f}% %{customdata[0]}<extra></extra>'
            )
        
        fig.update_layout(
            yaxis_title="Percent",
            xaxis_title="",
            height=300,
            margin=dict(l=40, r=20, t=30, b=40),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            ),
            paper_bgcolor=plot_bg,
            plot_bgcolor=plot_bg,
            font=dict(color=text_color),
            xaxis=dict(gridcolor=grid_color),
            yaxis=dict(gridcolor=grid_color, range=[0, 100])
        )
        # Prevent clipping of markers at edges
        fig.update_traces(cliponaxis=False)
        st.plotly_chart(fig, use_container_width=True)
    
    # Bottom row - Correlations and Teacher Reflections
    b1, b2 = st.columns(2)
    
    with b1:
        # Compact task selector using radio buttons (no full refresh)
        corr_task_filter = st.radio(
            "Correlations",
            ["All", "T1", "T2", "End"],
            horizontal=True,
            key="corr_task_radio"
        )
        
        # Map short names to full task names
        task_map = {
            "All": "All Tasks",
            "T1": "Instructional Task #1",
            "T2": "Instructional Task #2",
            "End": "End-of-Unit Performance Task"
        }
        full_task_name = task_map[corr_task_filter]
        
        # Filter by task type for correlations
        corr_filtered_df = filtered_df.copy()
        if full_task_name != "All Tasks":
            corr_filtered_df = corr_filtered_df[corr_filtered_df["Task"] == full_task_name]
        
        if len(corr_filtered_df) > 0:
            corr_data = corr_filtered_df[["Engaged", "Choice", "Prepared", "Confused"]].copy()
            corr_data = corr_data.replace({"Yes": 1, "No": 0})
            corr_data = corr_data.apply(pd.to_numeric, errors="coerce")
            corr_matrix = corr_data.corr()
            
            # Display as styled HTML table - 200px to align with reflections bottom
            html = f"""
            <div style="background-color: {plot_bg}; padding: 10px; border-radius: 5px; height: 200px; overflow-y: auto;">
            <table style="width: 100%; border-collapse: collapse; color: {text_color};">
                <thead>
                    <tr style="border-bottom: 1px solid {grid_color};">
                        <th style="padding: 4px; text-align: left; font-size: 0.85em;"></th>
                        <th style="padding: 4px; text-align: center; font-size: 0.85em;">Engaged</th>
                        <th style="padding: 4px; text-align: center; font-size: 0.85em;">Choice</th>
                        <th style="padding: 4px; text-align: center; font-size: 0.85em;">Prepared</th>
                        <th style="padding: 4px; text-align: center; font-size: 0.85em;">Confused</th>
                    </tr>
                </thead>
                <tbody>
            """
            
            for idx in corr_matrix.index:
                html += f'<tr style="border-bottom: 1px solid {grid_color};">'
                html += f'<td style="padding: 4px; font-weight: bold; font-size: 0.85em;">{idx}</td>'
                for col in corr_matrix.columns:
                    val = corr_matrix.loc[idx, col]
                    html += f'<td style="padding: 4px; text-align: center; font-size: 0.85em;">{val:.2f}</td>'
                html += '</tr>'
            
            html += """
                </tbody>
            </table>
            </div>
            """
            
            st.markdown(html, unsafe_allow_html=True)
        else:
            st.write("No data")
    
    with b2:
        st.write("**Teacher Reflections**")
        
        # Filter by date
        filtered_teacher_df = teacher_df[
            (teacher_df["Timestamp"] >= pd.to_datetime(start_date)) & 
            (teacher_df["Timestamp"] <= pd.to_datetime(end_date))
        ]
        
        # Filter by teacher
        if st.session_state.username == "admin":
            # Admin view
            if teacher_filter == "Select a teacher...":
                # Show message when no teacher selected
                filtered_teacher_df = filtered_teacher_df[0:0]  # Empty
            else:
                # Filter to specific teacher
                filtered_teacher_df = filtered_teacher_df[
                    filtered_teacher_df["FullName"].str.lower().str.contains(teacher_filter.lower(), na=False)
                ]
        else:
            # Regular teacher view - only their reflections
            filtered_teacher_df = filtered_teacher_df[
                filtered_teacher_df["FullName"].str.lower().str.contains(st.session_state.username.lower(), na=False)
            ]
        
        # Scrollable container - 240px height
        reflections_container = st.container(height=240)
        
        with reflections_container:
            if st.session_state.username == "admin" and teacher_filter == "Select a teacher...":
                st.write("*Select a teacher to view reflections*")
            elif len(filtered_teacher_df) == 0:
                st.write("*No reflections in this date range*")
            else:
                for idx, row in filtered_teacher_df.iterrows():
                    with st.expander(f"{row['FullName']} - {row['Timestamp'].strftime('%m/%d/%Y')}"):
                        st.write(f"**Task:** {row['TaskType']}")
                        st.write(f"**Went well:** {row['WentWell']}")
                        st.write(f"**Struggled:** {row['Struggled']}")

with col_chat:
    st.write("### AI Analysis")
    
    # Fixed height scrollable container for chat
    chat_container = st.container(height=600)
    
    with chat_container:
        # Show FAQ buttons if no chat history
        if len(st.session_state.chat_history) == 0:
            st.write("**Get started with a question:**")
            
            col_faq1, col_faq2 = st.columns(2)
            
            with col_faq1:
                if st.button("What patterns do you see?", use_container_width=True):
                    st.session_state.pending_question = "What patterns do you see in the data?"
                    st.rerun()
                
                if st.button("How's student choice?", use_container_width=True):
                    st.session_state.pending_question = "How are students responding to having choice?"
                    st.rerun()
            
            with col_faq2:
                if st.button("What's confusing students?", use_container_width=True):
                    st.session_state.pending_question = "What topics or tasks are confusing students the most?"
                    st.rerun()
                
                if st.button("How's engagement?", use_container_width=True):
                    st.session_state.pending_question = "How are engagement levels looking?"
                    st.rerun()
        
        # Display chat history
        for message in st.session_state.chat_history:
            with st.chat_message(message["role"]):
                st.write(message["content"])
    
    # Check for pending question from FAQ buttons
    if "pending_question" in st.session_state:
        prompt = st.session_state.pending_question
        del st.session_state.pending_question
    else:
        prompt = st.chat_input("Ask about the data...")
    
    # Chat input
    if prompt:
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        
        # Calculate stats from FULL dataset
        total_all = len(student_df)
        engaged_all = (student_df["Engaged"] == "Yes").sum() / total_all * 100
        confused_all = (student_df["Confused"] == "Yes").sum() / total_all * 100
        choice_all = (student_df["Choice"] == "Yes").sum() / total_all * 100
        prepared_all = (student_df["Prepared"] == "Yes").sum() / total_all * 100
        
        # Get recent comments
        recent = student_df.nlargest(15, "Timestamp")
        comments = "\n".join([
            f"• Liked: \"{row['LikedText']}\" | Disliked: \"{row['DislikedText']}\""
            for _, row in recent.iterrows()
            if row['LikedText'] or row['DislikedText']
        ])
        
        # For admin, include teacher reflections
        teacher_context = ""
        if st.session_state.username == "admin":
            recent_reflections = teacher_df.nlargest(10, "Timestamp")
            teacher_context = "\n\nRecent Teacher Reflections:\n"
            for _, row in recent_reflections.iterrows():
                teacher_context += f"• {row['FullName']}: Went well: \"{row['WentWell']}\" | Struggled: \"{row['Struggled']}\"\n"
        
        system_prompt = f"""Analyze student exit ticket data.

DATA (All Time, n={total_all}):
- Engaged: {engaged_all:.0f}%
- Confused: {confused_all:.0f}%  
- Choice: {choice_all:.0f}%
- Prepared: {prepared_all:.0f}%

Sample Student Comments:
{comments}{teacher_context}

Question: {prompt}

Write 2-3 short paragraphs. Just dive in - NO introductory sentences. Focus on what students actually said. DO NOT write summary sentences or conclusions."""
        
        try:
            client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
            response = client.messages.create(
                model="claude-3-5-haiku-20241022",
                max_tokens=300,
                messages=[{"role": "user", "content": system_prompt}]
            )
            
            answer = response.content[0].text
            st.session_state.chat_history.append({"role": "assistant", "content": answer})
            
        except Exception as e:
            st.error(f"Error: {str(e)}")
        
        st.rerun()
