package com.bruceyangg.pulsedesk.ui.components

import java.util.Locale
import kotlin.math.abs

fun pctText(pct: Double?): String {
    if (pct == null || pct.isNaN()) return "—"
    val sign = if (pct > 0) "+" else ""
    return String.format(Locale.US, "%s%.2f%%", sign, pct)
}

fun priceText(price: Double?): String {
    if (price == null || price.isNaN()) return "—"
    return if (abs(price) >= 1000) {
        String.format(Locale.US, "%,.2f", price)
    } else {
        String.format(Locale.US, "%.2f", price)
    }
}
