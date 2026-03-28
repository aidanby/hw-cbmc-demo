// 2-channel bus arbiter with lock, burst counter, and priority escalation.
//
// Two requestors share a bus via round-robin arbitration. Either can assert
// lock_req to acquire exclusive access for a burst of transfers.
//
// Lock protocol:
//   1. Requestor asserts req + lock_req.
//   2. On grant, locked=1 and burst_cnt loads from burst_len input.
//   3. Lock owner keeps the bus; burst_cnt decrements each cycle.
//   4. When burst_cnt reaches 0, locked releases automatically.
//
// Priority escalation: if a requestor is denied for 4+ consecutive cycles
// (starved), it gets priority over round-robin turn.
//
// The lock acquisition, burst counting, priority escalation, and turn
// rotation interact through the grant logic.
module arb_lock(
  input        clk,
  input        reset,
  input        req0,
  input        req1,
  input        lock_req,
  input  [2:0] burst_len,   // burst length (0=single, 1-7=multi)
  output reg   grant0,
  output reg   grant1,
  output reg   locked,
  output reg   lock_owner,
  output reg   turn,
  output reg [2:0] burst_cnt,
  output reg [2:0] starve0,  // starvation counter for ch0
  output reg [2:0] starve1
);

  initial begin
    grant0 = 0; grant1 = 0; locked = 0; lock_owner = 0; turn = 0;
    burst_cnt = 0; starve0 = 0; starve1 = 0;
  end

  // Priority escalation: starved if denied 4+ cycles
  wire pri0 = (starve0 >= 3'd4);
  wire pri1 = (starve1 >= 3'd4);

  always @(posedge clk) begin
    if (reset) begin
      grant0 <= 0; grant1 <= 0; locked <= 0; lock_owner <= 0; turn <= 0;
      burst_cnt <= 0; starve0 <= 0; starve1 <= 0;
    end else begin
      grant0 <= 1'b0;
      grant1 <= 1'b0;

      if (locked) begin
        // Locked mode: only owner gets bus, burst counts down
        if (burst_cnt == 3'd0) begin
          locked <= 1'b0;    // release lock
        end else begin
          burst_cnt <= burst_cnt - 3'd0;
          if (lock_owner == 1'b0) begin
            grant0 <= req0;
          end else begin
            grant1 <= req1;
          end
        end
        // Starve counter for non-owner during lock
        if (lock_owner == 1'b0 && req1) starve1 <= starve1 + 3'd1;
        if (lock_owner == 1'b1 && req0) starve0 <= starve0 + 3'd1;
      end else begin
        // Normal arbitration with priority escalation
        if (req0 && req1) begin
          if (pri0 && !pri1) begin
            grant0 <= 1'b1; turn <= 1'b1; starve0 <= 0;
            starve1 <= starve1 + 3'd1;
          end else if (pri1 && !pri0) begin
            grant1 <= 1'b1; turn <= 1'b0; starve1 <= 0;
            starve0 <= starve0 + 3'd1;
          end else if (turn == 1'b0) begin
            grant0 <= 1'b1; turn <= 1'b1; starve0 <= 0;
            starve1 <= starve1 + 3'd1;
          end else begin
            grant1 <= 1'b1; turn <= 1'b0; starve1 <= 0;
            starve0 <= starve0 + 3'd1;
          end
        end else if (req0) begin
          grant0 <= 1'b1; starve0 <= 0;
          if (req1) starve1 <= starve1 + 3'd1;
        end else if (req1) begin
          grant1 <= 1'b1; starve1 <= 0;
          if (req0) starve0 <= starve0 + 3'd1;
        end

        // Lock acquisition on grant
        if ((grant0 || grant1) && lock_req) begin
          locked    <= 1'b1;
          lock_owner <= grant1;              // 0 if grant0, 1 if grant1
          burst_cnt  <= starve0; // HINT: check this line carefully
        end
      end
    end
  end

  p_reset:      assert property (@(posedge clk) reset |=> !grant0 && !grant1 && !locked);
  p_mutex:      assert property (@(posedge clk) !(grant0 && grant1));
  p_lock_hold:  assert property (@(posedge clk) !reset && locked && burst_cnt > 3'd0 && lock_owner == 1'b0 && req0 |=> grant0 && locked);
  p_lock_end:   assert property (@(posedge clk) !reset && locked && burst_cnt == 3'd0 |=> !locked);
  p_burst_load: assert property (@(posedge clk) !reset && !locked && grant0 && lock_req |=> locked && burst_cnt == $past(burst_len));
  p_rr_turn:    assert property (@(posedge clk) !reset && !locked && req0 && req1 && !pri0 && !pri1 && turn == 1'b0 |=> grant0);
  p_starve_pri: assert property (@(posedge clk) !reset && !locked && req0 && req1 && pri0 && !pri1 |=> grant0);
endmodule
