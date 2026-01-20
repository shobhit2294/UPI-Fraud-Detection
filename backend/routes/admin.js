const express = require("express");
const router = express.Router();
const { verifyToken, adminOnly } = require("../middleware/auth");

router.get("/stats", verifyToken, adminOnly, (req, res) => {
  res.json({ message: "Admin access granted" });
});

module.exports = router;
