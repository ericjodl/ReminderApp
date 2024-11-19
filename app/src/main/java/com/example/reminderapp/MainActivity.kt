package com.example.reminderapp

import android.content.Intent
import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity
import com.example.reminderapp.databinding.ActivityMainBinding

class MainActivity : AppCompatActivity() {

    private lateinit var binding: ActivityMainBinding

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        // Verwende View Binding für activity_main.xml
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)

        // Button- oder FAB-Klicklistener zum Starten der CreateReminderActivity
        binding.fabAddReminder.setOnClickListener {
            val intent = Intent(this, CreateReminderActivity::class.java)
            startActivity(intent)
        }
    }
}
