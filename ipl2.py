
import streamlit as st
import mysql.connector
 
# ─────────────────────────────────────────
#  Database connection (cached so it is
#  created once per browser session)
# ─────────────────────────────────────────
@st.cache_resource
def get_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="8464",
        database="ipl_ticket_reservation_system"
    )
 
def get_cursor():
    return get_connection().cursor()
 
# ─────────────────────────────────────────
#  Session-state defaults
# ─────────────────────────────────────────
if "admin_password" not in st.session_state:
    st.session_state.admin_password = "admin123"
if "admin_logged_in" not in st.session_state:
    st.session_state.admin_logged_in = False
 
# ─────────────────────────────────────────
#  Page config & title
# ─────────────────────────────────────────
st.set_page_config(page_title="IPL Ticket System", page_icon="🏏", layout="centered")
st.title("🏏 IPL Ticket Reservation System")
st.markdown("---")
 
# ─────────────────────────────────────────
#  Sidebar navigation
# ─────────────────────────────────────────
menu = st.sidebar.radio(
    "Navigate",
    [
        "📅 View Match Schedule",
        "🎟️ Book Tickets",
        "🔍 View Booking Details",
        "❌ Cancel Tickets",
        "🔒 Admin Portal",
    ]
)
 
mydb = get_connection()
 
# ══════════════════════════════════════════
#  1. VIEW MATCH SCHEDULE
# ══════════════════════════════════════════
if menu == "📅 View Match Schedule":
    st.header("Current Match Schedule & Availability")
 
    mycursor = mydb.cursor()
    mycursor.execute(
        "SELECT Match_ID, Team_A, Team_B, Venue, Available_Seats, Ticket_Price FROM Matches"
    )
    records = mycursor.fetchall()
    mycursor.close()
 
    if not records:
        st.info("No matches are currently scheduled.")
    else:
        import pandas as pd
        df = pd.DataFrame(
            records,
            columns=["Match ID", "Team A", "Team B", "Venue", "Seats Available", "Price (₹)"]
        )
        df.insert(2, "Match", df["Team A"] + " vs " + df["Team B"])
        df = df.drop(columns=["Team A", "Team B"])
        st.dataframe(df, use_container_width=True, hide_index=True)
 
# ══════════════════════════════════════════
#  2. BOOK TICKETS
# ══════════════════════════════════════════
elif menu == "🎟️ Book Tickets":
    st.header("Book Your Tickets")
 
    match_id = st.number_input("Enter Match ID", min_value=1, step=1)
 
    if st.button("Check Match"):
        mycursor = mydb.cursor()
        mycursor.execute(
            "SELECT Team_A, Team_B, Available_Seats, Ticket_Price FROM Matches WHERE Match_ID = %s",
            (match_id,)
        )
        match_data = mycursor.fetchone()
        mycursor.close()
 
        if match_data:
            st.session_state["match_data"] = match_data
            st.session_state["booking_match_id"] = match_id
        else:
            st.error("❌ Match ID not found in the database.")
            st.session_state.pop("match_data", None)
 
    if "match_data" in st.session_state:
        team_a, team_b, available_seats, ticket_price = st.session_state["match_data"]
        st.success(f"Match Found: **{team_a} vs {team_b}**")
        st.write(f"🪑 Available Seats: **{available_seats}**")
        st.write(f"💰 Price per Ticket: **₹{ticket_price}**")
 
        if available_seats == 0:
            st.warning("⚠️ This match is completely sold out.")
        else:
            with st.form("booking_form"):
                customer_name = st.text_input("Customer Name")
                tickets_needed = st.number_input(
                    "Number of Tickets", min_value=1, max_value=int(available_seats), step=1
                )
                total_cost = tickets_needed * ticket_price
                st.info(f"Total Amount Due: ₹{total_cost}")
                submitted = st.form_submit_button("Confirm & Pay")
 
            if submitted:
                if not customer_name.strip():
                    st.error("Please enter a customer name.")
                elif tickets_needed > available_seats:
                    st.error(f"Only {available_seats} seats left. Reduce ticket count.")
                else:
                    mycursor = mydb.cursor()
                    try:
                        mycursor.execute(
                            "UPDATE Matches SET Available_Seats = Available_Seats - %s WHERE Match_ID = %s",
                            (tickets_needed, st.session_state["booking_match_id"])
                        )
                        mycursor.execute(
                            "INSERT INTO Bookings (Match_ID, Customer_Name, Tickets_Bought, Total_Cost) VALUES (%s, %s, %s, %s)",
                            (st.session_state["booking_match_id"], customer_name, tickets_needed, total_cost)
                        )
                        mydb.commit()
                        booking_id = mycursor.lastrowid
                        st.success(f"✅ Payment Successful! Booking ID: **{booking_id}**")
                        st.balloons()
                        del st.session_state["match_data"]
                    except Exception as e:
                        mydb.rollback()
                        st.error(f"Database error: {e}")
                    finally:
                        mycursor.close()
 
# ══════════════════════════════════════════
#  3. VIEW BOOKING DETAILS
# ══════════════════════════════════════════
elif menu == "🔍 View Booking Details":
    st.header("View Booking Details")
 
    booking_id = st.number_input("Enter Booking ID", min_value=1, step=1)
 
    if st.button("Fetch Booking"):
        mycursor = mydb.cursor()
        mycursor.execute(
            """
            SELECT b.Booking_ID, b.Customer_Name, b.Tickets_Bought, b.Total_Cost,
                   m.Team_A, m.Team_B, m.Venue, m.Match_Date
            FROM Bookings b, Matches m
            WHERE b.Match_ID = m.Match_ID AND b.Booking_ID = %s
            """,
            (booking_id,)
        )
        ticket_data = mycursor.fetchone()
        mycursor.close()
 
        if ticket_data:
            b_id, name, tickets, cost, team_a, team_b, venue, date = ticket_data
            st.markdown("### 🎫 Official Match Ticket")
            st.markdown("---")
            col1, col2 = st.columns(2)
            col1.metric("Booking ID", b_id)
            col1.write(f"**Issued To:** {name}")
            col1.write(f"**Match:** {team_a} vs {team_b}")
            col2.write(f"**Venue:** {venue}")
            col2.write(f"**Date:** {date}")
            col2.metric("Seats Booked", tickets)
            col2.metric("Total Paid", f"₹{cost}")
        else:
            st.error(f"No booking found with ID {booking_id}.")
 
# ══════════════════════════════════════════
#  4. CANCEL TICKETS
# ══════════════════════════════════════════
elif menu == "❌ Cancel Tickets":
    st.header("Cancel Tickets")
 
    booking_id = st.number_input("Enter Booking ID to Cancel", min_value=1, step=1)
 
    if st.button("Look Up Booking"):
        mycursor = mydb.cursor()
        mycursor.execute(
            """
            SELECT b.Customer_Name, b.Tickets_Bought, b.Total_Cost,
                   m.Team_A, m.Team_B, b.Match_ID, m.Ticket_Price
            FROM Bookings b, Matches m
            WHERE b.Match_ID = m.Match_ID AND b.Booking_ID = %s
            """,
            (booking_id,)
        )
        booking_data = mycursor.fetchone()
        mycursor.close()
 
        if booking_data:
            st.session_state["cancel_data"] = booking_data
            st.session_state["cancel_booking_id"] = booking_id
        else:
            st.error(f"No booking found with ID {booking_id}.")
            st.session_state.pop("cancel_data", None)
 
    if "cancel_data" in st.session_state:
        name, tickets_bought, total_cost, team_a, team_b, match_id, ticket_price = st.session_state["cancel_data"]
        st.success(f"Booking Found for **{name}**")
        st.write(f"Match: **{team_a} vs {team_b}**")
        st.write(f"Total Seats Booked: **{tickets_bought}**")
 
        with st.form("cancel_form"):
            cancel_count = st.number_input(
                f"How many tickets to cancel? (1 – {tickets_bought})",
                min_value=1, max_value=int(tickets_bought), step=1
            )
            refund = cancel_count * ticket_price
            st.info(f"Refund Amount: ₹{refund}")
            confirm_cancel = st.form_submit_button("Confirm Cancellation")
 
        if confirm_cancel:
            mycursor = mydb.cursor()
            try:
                # Restore seats in Matches
                mycursor.execute(
                    "UPDATE Matches SET Available_Seats = Available_Seats + %s WHERE Match_ID = %s",
                    (cancel_count, match_id)
                )
 
                if cancel_count == tickets_bought:
                    # Full cancellation
                    mycursor.execute(
                        "DELETE FROM Bookings WHERE Booking_ID = %s",
                        (st.session_state["cancel_booking_id"],)
                    )
                    mydb.commit()
                    st.success(f"✅ Full Cancellation Successful! Refund: ₹{refund}")
                else:
                    # Partial cancellation
                    mycursor.execute(
                        """
                        UPDATE Bookings
                        SET Tickets_Bought = Tickets_Bought - %s, Total_Cost = Total_Cost - %s
                        WHERE Booking_ID = %s
                        """,
                        (cancel_count, refund, st.session_state["cancel_booking_id"])
                    )
                    mydb.commit()
                    remaining = tickets_bought - cancel_count
                    st.success(
                        f"✅ Partial Cancellation! {cancel_count} ticket(s) cancelled. "
                        f"Refund: ₹{refund}. Remaining tickets: {remaining}"
                    )
 
                del st.session_state["cancel_data"]
 
            except Exception as e:
                mydb.rollback()
                st.error(f"Database error: {e}")
            finally:
                mycursor.close()
 
# ══════════════════════════════════════════
#  5. ADMIN PORTAL
# ══════════════════════════════════════════
elif menu == "🔒 Admin Portal":
    st.header("Admin Portal")
 
    if not st.session_state.admin_logged_in:
        with st.form("admin_login"):
            pwd = st.text_input("Enter Admin Password", type="password")
            login_btn = st.form_submit_button("Login")
        if login_btn:
            if pwd == st.session_state.admin_password:
                st.session_state.admin_logged_in = True
                st.rerun()
            else:
                st.error("❌ Access Denied. Incorrect Password.")
    else:
        st.success("✅ Access Granted.")
        admin_action = st.radio("Admin Menu", ["Add a New Match", "Change Admin Password", "Logout"])
 
        if admin_action == "Add a New Match":
            st.subheader("Add New Match")
            with st.form("add_match_form"):
                match_id    = st.number_input("Match ID (numbers only)", min_value=1, step=1)
                team_a      = st.text_input("Team A (e.g., CSK)")
                team_b      = st.text_input("Team B (e.g., MI)")
                venue       = st.text_input("Venue")
                date        = st.date_input("Match Date")
                total_seats = st.number_input("Stadium Capacity", min_value=1, step=1)
                price       = st.number_input("Ticket Price (₹)", min_value=0.0, step=50.0)
                add_btn     = st.form_submit_button("Add Match")
 
            if add_btn:
                mycursor = mydb.cursor()
                try:
                    mycursor.execute(
                        """
                        INSERT INTO Matches
                        (Match_ID, Team_A, Team_B, Venue, Match_Date, Total_Seats, Available_Seats, Ticket_Price)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (int(match_id), team_a, team_b, venue, str(date),
                         int(total_seats), int(total_seats), float(price))
                    )
                    mydb.commit()
                    st.success(f"✅ {team_a} vs {team_b} added successfully!")
                except mysql.connector.IntegrityError:
                    st.error(f"❌ Match ID {match_id} already exists!")
                except Exception as e:
                    mydb.rollback()
                    st.error(f"Database error: {e}")
                finally:
                    mycursor.close()
 
        elif admin_action == "Change Admin Password":
            st.subheader("Change Password")
            with st.form("change_pwd_form"):
                old_pwd     = st.text_input("Old Password", type="password")
                new_pwd     = st.text_input("New Password", type="password")
                confirm_pwd = st.text_input("Confirm New Password", type="password")
                change_btn  = st.form_submit_button("Change Password")
 
            if change_btn:
                if old_pwd != st.session_state.admin_password:
                    st.error("Incorrect old password.")
                elif new_pwd != confirm_pwd:
                    st.error("New passwords do not match.")
                elif not new_pwd:
                    st.error("Password cannot be empty.")
                else:
                    st.session_state.admin_password = new_pwd
                    st.success("✅ Password changed successfully!")
 
        elif admin_action == "Logout":
            st.session_state.admin_logged_in = False
            st.rerun()
        #program done