package com.example.reminderapp

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.LiveData
import androidx.lifecycle.MutableLiveData
import androidx.lifecycle.viewModelScope
import com.example.reminderapp.data.Reminder
import com.example.reminderapp.data.ReminderDatabase
import kotlinx.coroutines.launch

class ReminderViewModel(application: Application) : AndroidViewModel(application) {

    private val reminderDao = ReminderDatabase.getDatabase(application).reminderDao()
    private val _reminders = MutableLiveData<List<Reminder>>()
    val reminders: LiveData<List<Reminder>> get() = _reminders

    // Lade alle Erinnerungen aus der Datenbank
    fun loadReminders() {
        viewModelScope.launch {
            _reminders.postValue(reminderDao.getAllReminders())
        }
    }

    // Neue Erinnerung hinzufügen
    fun addReminder(reminder: Reminder) {
        viewModelScope.launch {
            reminderDao.insert(reminder)
            loadReminders() // Liste aktualisieren
        }
    }
}
