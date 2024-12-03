package com.example.reminderapp.data

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.Query
import com.example.reminderapp.data.Reminder

@Dao
interface ReminderDao {
    @Insert
    suspend fun insert(reminder: Reminder)

    @Query("SELECT * FROM reminders")
    suspend fun getAllReminders(): List<Reminder>
}