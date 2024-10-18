import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date, timedelta
import os
import requests

# Set the page layout to wide
st.set_page_config(page_title="Daily Expense Tracker", layout="wide")

# Load or initialize the data
def load_data():
    if os.path.exists('expenses.csv'):
        return pd.read_csv('expenses.csv')
    else:
        return pd.DataFrame(columns=['Date', 'Category', 'Amount', 'Currency', 'Converted Amount', 'Description', 'EMI', 'Installments Left'])

def save_data(df):
    df.to_csv('expenses.csv', index=False)

# Load or initialize category budgets
def load_category_budgets():
    if os.path.exists('category_budgets.csv'):
        return pd.read_csv('category_budgets.csv')
    else:
        return pd.DataFrame(columns=['Category', 'Budget Type', 'Budget'])

def save_category_budgets(df):
    df.to_csv('category_budgets.csv', index=False)

# Initialize session state for page navigation and budget settings
if 'page' not in st.session_state:
    st.session_state.page = 'input'
if 'limit_set' not in st.session_state:
    st.session_state.limit_set = False

# Load the data
df = load_data()

if not df.empty:
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')

# Load the category budgets
category_budgets_df = load_category_budgets()

# --- Input Page ---
if st.session_state.page == 'input':
    st.title('💸 Daily Expense Tracker')

    # Create two columns: left (input form), right (table and graphs)
    col1, col2 = st.columns([1, 2])

    # --- Input Section in left column ---
    with col1:
        st.header('Add New Expense')

        # Date, Category, Amount, and Description
        expense_date = st.date_input('Date', date.today())
        category = st.selectbox('Category', ['Groceries', 'Utilities', 'Entertainment', 'Health', 'Transportation', 'Other'])

        # Multi-Currency Support
        st.subheader('Multi-Currency Support')
        base_currency = st.selectbox('Base Currency', ['USD', 'EUR', 'INR', 'GBP', 'JPY'], index=0)
        expense_currency = st.selectbox('Expense Currency', ['USD', 'EUR', 'INR', 'GBP', 'JPY'], index=0)
        amount_in_currency = st.number_input(f'Amount in {expense_currency}', min_value=0.0, format="%.2f")

        # Convert the amount to base currency
        converted_amount = amount_in_currency  # Default case when the base and expense currency are the same

        if expense_currency != base_currency:
            try:
                # Fetch conversion rates
                API_KEY = 'YOUR_API_KEY'  # Replace with your actual API key
                API_URL = f'https://v6.exchangerate-api.com/v6/{API_KEY}/latest/{expense_currency}'
                response = requests.get(API_URL)
                data = response.json()

                if response.status_code != 200 or data['result'] != 'success':
                    st.error(f"Failed to fetch conversion rates: {data.get('error-type', 'Unknown error')}")
                else:
                    conversion_rate = data['conversion_rates'][base_currency]
                    converted_amount = amount_in_currency * conversion_rate
                    st.write(f'{amount_in_currency} {expense_currency} is {converted_amount:.2f} {base_currency}')
            except Exception as e:
                st.error(f"An error occurred while fetching conversion rates: {e}")

        description = st.text_input('Description')

        # EMI options
        is_emi = st.checkbox('Is this an EMI?')
        installments_left = 0
        if is_emi:
            installments_left = st.number_input('Installments Left', min_value=1)

        if st.button('Add Expense'):
            # Create a new entry as a DataFrame row
            new_expense = pd.DataFrame({
                'Date': [expense_date],
                'Category': [category],
                'Amount': [converted_amount],  # Store the amount in base currency
                'Currency': [expense_currency],  # Track the original currency
                'Converted Amount': [converted_amount],  # Store the converted amount
                'Description': [description],
                'EMI': ['Yes' if is_emi else 'No'],
                'Installments Left': [installments_left]
            })

            # Concatenate the new entry to the existing DataFrame
            df = pd.concat([df, new_expense], ignore_index=True)
            save_data(df)
            st.success('Expense added successfully!')

        # --- Limit Section ---
        st.header("Set Spending Limit")

        # User input for limit period (daily, weekly, monthly)
        limit_type = st.selectbox("Limit Period", ["Daily", "Weekly", "Monthly"])
        spending_limit = st.number_input(f"Set {limit_type} Limit in {base_currency}", min_value=0.0, format="%.2f")

        # Save limit in session state
        if st.button('Set Limit'):
            st.session_state.limit = spending_limit
            st.session_state.limit_type = limit_type
            st.session_state.limit_set = True
            st.success(f"{limit_type} spending limit of {spending_limit} {base_currency} has been set!")

    # --- Display Section in right column ---
    with col2:
        st.header('Your Expenses')
        st.dataframe(df)

        # --- Display Category Budgets just below the expense table ---
        st.header('Category Budgets')
        if not category_budgets_df.empty:
            st.dataframe(category_budgets_df)
        else:
            st.info("No category budgets have been set yet.")

        # Button to navigate to the graph visualization page
        if st.button('Visualize'):
            st.session_state.page = 'visualize'

    # --- Category Budgets Section ---
    st.subheader("Add or Update Category Budgets")
    category = st.selectbox("Select Category", ['Groceries', 'Utilities', 'Entertainment', 'Health', 'Transportation', 'Other'])
    budget_type = st.selectbox("Budget Period", ["Weekly", "Monthly"])
    category_budget = st.number_input(f"Set {budget_type} Budget for {category} in {base_currency}", min_value=0.0, format="%.2f")

    if st.button('Set Category Budget'):
        # Save the budget into the DataFrame and CSV
        new_budget = pd.DataFrame({
            'Category': [category],
            'Budget Type': [budget_type],
            'Budget': [category_budget]
        })

        # Check if the category budget already exists and update it, otherwise add a new one
        existing_budget = category_budgets_df[
            (category_budgets_df['Category'] == category) & 
            (category_budgets_df['Budget Type'] == budget_type)
        ]

        if not existing_budget.empty:
            category_budgets_df.loc[
                (category_budgets_df['Category'] == category) & 
                (category_budgets_df['Budget Type'] == budget_type),
                'Budget'
            ] = category_budget
        else:
            category_budgets_df = pd.concat([category_budgets_df, new_budget], ignore_index=True)

        save_category_budgets(category_budgets_df)
        st.success(f"{budget_type} budget of {category_budget} {base_currency} set for {category}!")

# --- Notify if expenses exceed the limit ---
if st.session_state.limit_set:
    today = date.today()
    if st.session_state.limit_type == "Daily":
        filtered_df = df[df['Date'] == pd.to_datetime(today)]
    elif st.session_state.limit_type == "Weekly":
        week_start = today - timedelta(days=today.weekday())
        filtered_df = df[(df['Date'] >= pd.to_datetime(week_start)) & (df['Date'] <= pd.to_datetime(today))]
    elif st.session_state.limit_type == "Monthly":
        month_start = today.replace(day=1)
        filtered_df = df[(df['Date'] >= pd.to_datetime(month_start)) & (df['Date'] <= pd.to_datetime(today))]

    total_expenses = filtered_df['Amount'].sum()

    # Checking if expenses exceed the limit and playing audio if true
    if total_expenses >= st.session_state.limit:
        st.error(f"Warning: You have exceeded your {st.session_state.limit_type.lower()} limit!")
        
        # Play the alert sound
        audio_file = open('alert_sound.mp3', 'rb')
        st.audio(audio_file.read(), format='audio/mp3', autoplay=True)

# --- Visualization Page ---
elif st.session_state.page == 'visualize':
    st.title('📊 Expense Visualization')

    # Date range filter
    st.header('Filter by Date')
    start_date = st.date_input('Start Date', df['Date'].min().date() if not df.empty else date.today())
    end_date = st.date_input('End Date', df['Date'].max().date() if not df.empty else date.today())

    start_date = pd.to_datetime(start_date)
    end_date = pd.to_datetime(end_date)

    mask = (df['Date'] >= start_date) & (df['Date'] <= end_date)
    filtered_df = df.loc[mask]

    # --- First row: Category Breakdown (Bar chart) and EMI vs Non-EMI (Pie chart) ---
    row1_col1, row1_col2 = st.columns(2)

    with row1_col1:
        if not filtered_df.empty:
            fig = px.bar(filtered_df, x='Category', y='Amount', color='Category', title='Expenses by Category')
            st.plotly_chart(fig)
        else:
            st.warning('No expenses found for the selected date range.')

    with row1_col2:
        if not filtered_df.empty:
            fig_pie = px.pie(filtered_df, names='EMI', values='Amount', title='EMI vs Non-EMI Expenses')
            st.plotly_chart(fig_pie)
        else:
            st.warning('No expenses found for the selected date range.')

    # --- Second row: EMI Payments (Bar chart) ---
    st.header('EMI Payments')
    if not filtered_df.empty:
        emi_expenses = filtered_df[filtered_df['EMI'] == 'Yes']
        if not emi_expenses.empty:
            fig_emi = px.bar(emi_expenses, x='Date', y='Amount', color='Category', title='EMI Expenses Over Time')
            st.plotly_chart(fig_emi)
        else:
            st.info('No EMI expenses recorded for the selected date range.')
    else:
        st.info('No expenses found for the selected date range.')

    # --- Visualize Category Budgets ---
    st.header('Category Budgets Visualization')
    if not category_budgets_df.empty:
        fig_budgets = px.bar(category_budgets_df, x='Category', y='Budget', color='Budget Type', barmode='group', title='Category Budgets')
        st.plotly_chart(fig_budgets)
    else:
        st.info("No category budgets found for visualization.")

    # --- Back Button ---
    if st.button('Back'):
        st.session_state.page = 'input'
