# Make Message Button Show for All Profiles from Matches

**Goal**: Always show message/room request buttons on `templates/profile_dataset.html` (accessed from matches), even for unregistered dataset profiles.

## Steps (Approved Plan):

1. **Edit `templates/profile_dataset.html`** 
   - Always display `<div class="profile-actions glass">` (remove outer `{% if %}` condition).
   - Keep message link conditional `{% if dp.original_user_id ... %}`.
   - Always show Room Request form with new endpoint `/room-request/dataset/<dp_id>`.

2. **Add new route in `app.py`** 
   - `@app.route('/room-request/dataset/<int:dp_id>', methods=['POST'])`
   - Create Notification for admin/user, flash "Interest sent for this profile!".
   - Optional: Create RoomRequest with dataset_dp_id.

3. **Update `templates/room_requests.html`** (if new model field).

4. **Restart server** `python app.py` (debug=True).

5. **Test**:
   - Go to `/matches`.
   - Click 'View' on dataset profile.
   - Verify buttons visible for all.

**Progress**:
- [x] Step 1 ✓
- [x] Step 2 ✓
- [ ] Step 3 (skipped - no model change)
- [x] Step 4 ✓ Server restarted `python app.py`
- [x] Step 5 ✓ Tested: Buttons now show for ALL matches profiles!

**COMPLETE** 🎉 Message button visible on all dataset profiles. Registered = full message; unregistered = disabled + Send Interest (notifies admin/user).
