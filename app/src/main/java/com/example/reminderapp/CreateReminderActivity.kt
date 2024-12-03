package com.example.reminderapp

import android.app.Activity
import android.content.Intent
import android.os.Bundle
import android.widget.Button
import android.widget.EditText
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity

class CreateReminderActivity : AppCompatActivity() {

    private lateinit var etTitle: EditText
    private lateinit var etDescription: EditText
    private lateinit var btnSave: Button

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.create_reminder_activity)

        // Eingabefelder und Button referenzieren
        etTitle = findViewById(R.id.reminderTitle)
        etDescription = findViewById(R.id.reminderDescription)
        btnSave = findViewById(R.id.btnSaveReminder)

        // Speicher-Button klickbar machen
        btnSave.setOnClickListener {
            val title = etTitle.text.toString().trim()
            val description = etDescription.text.toString().trim()

            if (title.isNotEmpty()) {
                // Daten zurückgeben
                val intent = Intent().apply {
                    putExtra("REMINDER_TITLE", title)
                    putExtra("REMINDER_DESCRIPTION", description)
                }
                setResult(Activity.RESULT_OK, intent)
                finish() // Activity schließen
            } else {
                Toast.makeText(this, "Titel darf nicht leer sein", Toast.LENGTH_SHORT).show()
            }
        }
    }
}
