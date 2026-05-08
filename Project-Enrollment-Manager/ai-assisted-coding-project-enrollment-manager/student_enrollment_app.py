from __future__ import annotations

import pandas as pd
import streamlit as st

from enrollment_starter import (
    CURRENT_STUDENT,
    create_tables,
    seed_sample_data,
    get_available_course_keys,
    get_student_enrollments,
    get_student_enrollment_history,
    get_student_summary,
    enroll_with_key,
    soft_unenroll_student,
)


def setup_app() -> None:
    """Prepare the database and session state for the Streamlit UI."""
    create_tables()
    seed_sample_data()

    if "page" not in st.session_state:
        st.session_state.page = "Dashboard"
    if "selected_class" not in st.session_state:
        st.session_state.selected_class = None
    if "role" not in st.session_state:
        st.session_state.role = "student"
    if "feedback_message" not in st.session_state:
        st.session_state.feedback_message = ""
    if "feedback_type" not in st.session_state:
        st.session_state.feedback_type = "success"


def show_feedback() -> None:
    """Show short feedback messages stored in session state."""
    message = st.session_state.get("feedback_message", "")
    feedback_type = st.session_state.get("feedback_type", "success")

    if not message:
        return

    if feedback_type == "success":
        st.success(message)
    elif feedback_type == "warning":
        st.warning(message)
    else:
        st.error(message)


def go_to_dashboard() -> None:
    st.session_state.page = "Dashboard"
    st.session_state.selected_class = None


def go_to_class(course: dict) -> None:
    st.session_state.selected_class = course
    st.session_state.page = "Class Details"


def dashboard_page() -> None:
    """Student dashboard page."""
    student = CURRENT_STUDENT
    user_id = student["user_id"]
    email = student["email"]

    st.title("Student Enrollment Dashboard")
    st.caption(f"Logged in as {student['name']} ({email})")

    # Role check required by the assignment. The UI assumes the user is already logged in.
    if st.session_state.role != "student":
        st.error("You must be signed in as a student to use this page.")
        return

    show_feedback()

    summary = get_student_summary(user_id)
    col1, col2, col3 = st.columns(3)
    col1.metric("Current classes", summary["enrolled"])
    col2.metric("Unenrolled records", summary["unenrolled"])
    col3.metric("Total records", summary["total_records"])

    st.divider()

    st.subheader("Enroll in a Class")
    with st.form("enrollment_form"):
        enrollment_key = st.text_input("Enrollment key", placeholder="Example: DATA210-SPRING")
        submitted = st.form_submit_button("Enroll / Re-enroll")

    if submitted:
        result = enroll_with_key(user_id, email, enrollment_key)
        if result:
            st.session_state.feedback_message = f"You are now enrolled in {result['course_id']}."
            st.session_state.feedback_type = "success"
            st.session_state.selected_class = result
            st.session_state.page = "Class Details"
            st.rerun()
        else:
            st.session_state.feedback_message = "That enrollment key is invalid. Please check the key and try again."
            st.session_state.feedback_type = "error"
            st.rerun()

    st.subheader("My Enrolled Classes")
    enrolled_classes = get_student_enrollments(user_id)

    if not enrolled_classes:
        st.warning("You are not currently enrolled in any classes.")
    else:
        for course in enrolled_classes:
            with st.container(border=True):
                left, right = st.columns([3, 1])
                with left:
                    st.write(f"### {course['course_id']}: {course['course_name']}")
                    st.caption(f"Instructor: {course['instructor']} | Status: {course['status']}")
                with right:
                    if st.button("Go to Class", key=f"go_{course['course_id']}"):
                        go_to_class(course)
                        st.rerun()
                    if st.button("Unenroll", key=f"unenroll_{course['course_id']}"):
                        success = soft_unenroll_student(user_id, course["course_id"])
                        if success:
                            st.session_state.feedback_message = f"You have been unenrolled from {course['course_id']}."
                            st.session_state.feedback_type = "warning"
                        else:
                            st.session_state.feedback_message = "Unable to unenroll from that class."
                            st.session_state.feedback_type = "error"
                        go_to_dashboard()
                        st.rerun()

    with st.expander("Available practice enrollment keys"):
        st.dataframe(pd.DataFrame(get_available_course_keys()), use_container_width=True)

    with st.expander("Full enrollment history"):
        st.dataframe(pd.DataFrame(get_student_enrollment_history(user_id)), use_container_width=True)


def class_details_page() -> None:
    """Selected class page."""
    st.title("Class Details")

    selected_class = st.session_state.get("selected_class")
    if not selected_class:
        st.warning("No class is selected. Return to the dashboard and choose a class.")
        if st.button("Back to Dashboard"):
            go_to_dashboard()
            st.rerun()
        return

    show_feedback()

    st.container(border=True).write(
        f"""
        ### {selected_class['course_id']}: {selected_class.get('course_name', 'Selected Course')}
        **Instructor:** {selected_class.get('instructor', 'Not listed')}  
        **Status:** {selected_class.get('status', 'enrolled')}
        """
    )

    st.caption("This page appears after the student enrolls in a class or clicks Go to Class.")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Back to Dashboard"):
            go_to_dashboard()
            st.rerun()
    with col2:
        if st.button("Unenroll from this Class"):
            success = soft_unenroll_student(CURRENT_STUDENT["user_id"], selected_class["course_id"])
            if success:
                st.session_state.feedback_message = f"You have been unenrolled from {selected_class['course_id']}."
                st.session_state.feedback_type = "warning"
            else:
                st.session_state.feedback_message = "Unable to unenroll from that class."
                st.session_state.feedback_type = "error"
            go_to_dashboard()
            st.rerun()


def main() -> None:
    st.set_page_config(page_title="Student Enrollment", page_icon="🎓", layout="wide")
    setup_app()

    st.sidebar.title("Navigation")
    page_choice = st.sidebar.radio("Choose a page", ["Dashboard", "Class Details"])
    st.session_state.page = page_choice if page_choice == "Dashboard" else st.session_state.page

    st.sidebar.caption("Assumption: the student is already logged in. No login, registration, or password system is built.")
    st.sidebar.selectbox("Simulated role", ["student"], key="role")

    if st.session_state.page == "Class Details":
        class_details_page()
    else:
        dashboard_page()


if __name__ == "__main__":
    main()
