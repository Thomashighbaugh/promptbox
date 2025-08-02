"""
Renders the Streamlit UI for managing backups.
"""
import streamlit as st
from promptbox.services.backup_service import BackupService
from promptbox.core.config import settings

def render_backup_view(backup_service: BackupService):
    st.header("Backup & Restore")

    st.info(f"All backups are saved to: `{settings.backup_dir}`")

    st.subheader("Create Backups")
    st.markdown("Create a complete backup of your data. It's a good idea to do this regularly!")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if st.button("📦 Backup All Databases", use_container_width=True):
            with st.spinner("Backing up databases..."):
                results = backup_service.backup_all_core_databases()
                all_successful = True
                messages = []
                for success, message in results:
                    messages.append(message)
                    if not success:
                        all_successful = False

                if all_successful:
                    st.success("All databases backed up successfully.")
                    for msg in messages:
                        st.caption(msg)
                else:
                    st.error("One or more errors occurred during database backup:")
                    for msg in messages:
                        if "Successfully" in msg:
                            st.caption(msg)
                        else:
                            st.warning(msg)

    with col2:
        if st.button("📝 Backup Prompts to Markdown", use_container_width=True):
            with st.spinner("Exporting prompts to archive..."):
                success, message = backup_service.backup_prompts_to_archive()
                if success:
                    st.success(message)
                else:
                    st.error(message)

    with col3:
        if st.button("🎭 Backup Cards to Markdown", use_container_width=True):
            with st.spinner("Exporting cards to archive..."):
                success, message = backup_service.backup_cards_to_archive()
                if success:
                    st.success(message)
                else:
                    st.error(message)
    
    with col4:
        if st.button("💬 Backup Chat Logs to Markdown", use_container_width=True):
            with st.spinner("Exporting chat logs to archive..."):
                success, message = backup_service.backup_chats_to_archive()
                if success:
                    st.success(message)
                else:
                    st.error(message)

    st.markdown("---")

    st.subheader("Existing Backups")
    try:
        backup_dir = settings.backup_dir
        if not backup_dir.exists() or not any(backup_dir.iterdir()):
            st.info("No backup files found yet.")
        else:
            files = sorted(backup_dir.iterdir(), key=lambda f: f.stat().st_mtime, reverse=True)
            for f in files:
                st.code(f.name, language=None)
    except Exception as e:
        st.error(f"Could not read backup directory: {e}")