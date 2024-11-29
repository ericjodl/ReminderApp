package com.example.reminderapp

import android.content.Intent
import android.os.Bundle
import android.widget.Button
import android.widget.EditText
import androidx.appcompat.app.AppCompatActivity
import com.example.reminderapp.databinding.CreateReminderActivityBinding
import android.widget.Toast

class CreateReminderActivity : AppCompatActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.create_reminder_activity)

        val editText = findViewById<EditText>(R.id.etTitle)
        val btnSave = findViewById<Button>(R.id.btnSaveReminder)

        btnSave.setOnClickListener {
            val reminderText = editText.text.toString()

            if (reminderText.isNotEmpty()) {
                val intent = Intent()
                intent.putExtra("REMINDER_TEXT", reminderText)
                setResult(RESULT_OK, intent)
                finish() // Schließe die Activity und kehre zurück
            } else {
                Toast.makeText(this, "Bitte einen Text eingeben", Toast.LENGTH_SHORT).show()
            }
        }
    }
}
