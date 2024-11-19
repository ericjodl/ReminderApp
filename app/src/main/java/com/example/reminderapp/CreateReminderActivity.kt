package com.example.reminderapp

import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity
import com.example.reminderapp.databinding.CreateReminderActivityBinding
import android.widget.Toast

class CreateReminderActivity : AppCompatActivity() {

    private lateinit var binding: CreateReminderActivityBinding

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        // Verwende View Binding für create_reminder_activity.xml
        binding = CreateReminderActivityBinding.inflate(layoutInflater)
        setContentView(binding.root)

        // Beispiel: Klicklistener für den „Speichern“-Button
        binding.btnSaveReminder.setOnClickListener {
            Toast.makeText(this, "Erinnerung gespeichert!", Toast.LENGTH_SHORT).show()
            finish() // Zurück zur MainActivity
        }
    }
}
