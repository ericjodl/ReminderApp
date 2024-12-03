package com.example.reminderapp

import android.content.Intent
import android.os.Bundle
import androidx.activity.viewModels
import androidx.appcompat.app.AppCompatActivity
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import com.example.reminderapp.data.Reminder
import com.google.android.material.floatingactionbutton.FloatingActionButton

class MainActivity : AppCompatActivity() {

    private lateinit var recyclerView: RecyclerView
    private lateinit var adapter: ReminderAdapter
    private val reminderViewModel: ReminderViewModel by viewModels() // ViewModel zur Datenverwaltung

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        // RecyclerView und FloatingActionButton initialisieren
        recyclerView = findViewById(R.id.recyclerViewReminder)
        val btnCreateReminder = findViewById<FloatingActionButton>(R.id.fabAddReminder)

        // RecyclerView konfigurieren
        adapter = ReminderAdapter(mutableListOf())
        recyclerView.layoutManager = LinearLayoutManager(this)
        recyclerView.adapter = adapter

        // Reminder aus der Datenbank laden und anzeigen
        reminderViewModel.loadReminders()
        reminderViewModel.reminders.observe(this) { reminders ->
            adapter.updateData(reminders) // RecyclerView mit neuen Daten aktualisieren
        }

        // Button zum Erstellen einer neuen Erinnerung
        btnCreateReminder.setOnClickListener {
            val intent = Intent(this, CreateReminderActivity::class.java)
            startActivityForResult(intent, 1)
        }
    }

    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        if (requestCode == 1 && resultCode == RESULT_OK) {
            val title = data?.getStringExtra("REMINDER_TITLE") ?: return
            val description = data.getStringExtra("REMINDER_DESCRIPTION") ?: "Keine Beschreibung"

            // Neue Erinnerung in der Datenbank speichern
            val newReminder = Reminder(
                title = title,
                description = description,
                timestamp = System.currentTimeMillis()
            )
            reminderViewModel.addReminder(newReminder) // Speichern über ViewModel
        }
    }
}
